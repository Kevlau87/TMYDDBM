-- Gold: drain_attribution
--
-- First pass at the project's core hard problem: attributing battery-level
-- drops to a cause. Nothing in TeslaMate/Tesla's data labels this directly,
-- so this derives it by pairing consecutive battery_state_timeline pings
-- and tagging the delta with the state (and climate flag) active at the
-- time. This is a coarse first pass, not a solved problem -- "parked with
-- climate off" is a phantom-drain proxy, not a certainty (e.g. sentry mode,
-- preconditioning ahead of a scheduled departure, and other causes aren't
-- separately visible in this data yet).

CREATE OR REPLACE VIEW gold_drain_attribution AS
WITH ordered AS (
    SELECT
        car_id,
        state,
        is_climate_on,
        date,
        battery_level,
        LAG(date) OVER (PARTITION BY car_id ORDER BY date) AS prev_date,
        LAG(battery_level) OVER (PARTITION BY car_id ORDER BY date) AS prev_battery_level,
        LAG(state) OVER (PARTITION BY car_id ORDER BY date) AS prev_state
    FROM silver_battery_state_timeline
)
SELECT
    car_id,
    prev_date AS interval_start,
    date AS interval_end,
    date_diff('second', prev_date, date) AS duration_s,
    state,
    is_climate_on,
    prev_battery_level AS start_battery_level,
    battery_level AS end_battery_level,
    prev_battery_level - battery_level AS battery_level_drop,
    CASE
        WHEN state = 'driving' THEN 'driving'
        WHEN state = 'charging' THEN 'charging'
        WHEN state IN ('parked', 'asleep', 'online') AND is_climate_on THEN 'climate_while_parked'
        WHEN state IN ('parked', 'asleep', 'online') AND NOT is_climate_on THEN 'phantom_drain'
        ELSE 'unclassified'
    END AS drain_category
FROM ordered
WHERE prev_date IS NOT NULL
    AND state = prev_state;
