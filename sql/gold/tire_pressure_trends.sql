-- Gold: tire_pressure_trends
--
-- Tire pressure is logged on every position ping and drops measurably with
-- cold outside temperature -- a real early-warning signal, not just a dash
-- light. Unpivoted into long/tidy form (one row per tire per ping) since
-- that's what a color-by-tire line chart wants.

CREATE OR REPLACE VIEW gold_tire_pressure_trends AS
SELECT
    car_id,
    date,
    outside_temp,
    CASE tire
        WHEN 'tpms_pressure_fl' THEN 'Front Left'
        WHEN 'tpms_pressure_fr' THEN 'Front Right'
        WHEN 'tpms_pressure_rl' THEN 'Rear Left'
        WHEN 'tpms_pressure_rr' THEN 'Rear Right'
    END AS tire,
    pressure
FROM teslamate.public.positions
UNPIVOT (
    pressure FOR tire IN (
        tpms_pressure_fl, tpms_pressure_fr, tpms_pressure_rl, tpms_pressure_rr
    )
)
WHERE pressure IS NOT NULL;
