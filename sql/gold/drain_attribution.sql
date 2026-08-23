-- Gold: drain_attribution
--
-- First pass at the project's core hard problem: attributing battery-level
-- drops to a cause. Nothing in TeslaMate/Tesla's data labels this directly,
-- so this derives it by pairing consecutive battery_state_timeline pings
-- and tagging the delta with what was happening at the time. This is a
-- coarse first pass, not a solved problem -- "parked with climate off" is a
-- phantom-drain proxy, not a certainty (e.g. sentry mode, preconditioning
-- ahead of a scheduled departure, and other causes aren't separately
-- visible in this data yet).
--
-- is_driving/is_charging take priority over the state+climate fallback --
-- see silver_battery_state_timeline for why `states.state` alone isn't
-- reliable here. NULL is_climate_on (common: most position pings don't
-- carry climate telemetry) gets its own honest category rather than being
-- silently dropped or guessed as false.

CREATE OR REPLACE VIEW gold_drain_attribution AS
WITH ordered AS (
    SELECT
        car_id,
        state,
        is_driving,
        is_charging,
        is_climate_on,
        date,
        battery_level,
        LAG(date) OVER (PARTITION BY car_id ORDER BY date) AS prev_date,
        LAG(battery_level) OVER (PARTITION BY car_id ORDER BY date) AS prev_battery_level,
        LAG(state) OVER (PARTITION BY car_id ORDER BY date) AS prev_state,
        LAG(is_driving) OVER (PARTITION BY car_id ORDER BY date) AS prev_is_driving,
        LAG(is_charging) OVER (PARTITION BY car_id ORDER BY date) AS prev_is_charging
    FROM silver_battery_state_timeline
)
SELECT
    car_id,
    prev_date AS interval_start,
    date AS interval_end,
    date_diff('second', prev_date, date) AS duration_s,
    state,
    is_driving,
    is_charging,
    is_climate_on,
    prev_battery_level AS start_battery_level,
    battery_level AS end_battery_level,
    prev_battery_level - battery_level AS battery_level_drop,
    CASE
        WHEN is_driving THEN 'driving'
        WHEN is_charging THEN 'charging'
        WHEN is_climate_on IS TRUE THEN 'climate_while_parked'
        WHEN is_climate_on IS FALSE THEN 'phantom_drain'
        ELSE 'parked_unknown_climate'
    END AS drain_category
FROM ordered
WHERE prev_date IS NOT NULL
    AND state = prev_state
    AND is_driving = prev_is_driving
    AND is_charging = prev_is_charging;
