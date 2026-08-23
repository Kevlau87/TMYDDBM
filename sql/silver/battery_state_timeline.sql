-- Silver: battery_state_timeline
--
-- TeslaMate's own tables (charging_processes, drives) only cover the
-- charging and driving states. They don't tell us what happened to the
-- battery while the car was just parked or asleep -- which is exactly where
-- phantom drain and climate-while-parked live. This view is the raw
-- material for that: every position ping (regardless of drive_id), paired
-- with whichever `states` interval it falls inside, so battery-level deltas
-- can be attributed to a state rather than assumed.
--
-- is_driving/is_charging are derived independently of `states.state`: on
-- the first real dataset this ran against, `states` never actually emitted
-- 'driving' or 'charging' -- it stayed 'online' through an entire real
-- drive and charge. Relying on `state` alone would silently misattribute
-- both. is_driving comes straight from drive_id; is_charging comes from
-- whether the ping falls inside a charging_processes window for the car.
--
-- This is deliberately NOT pre-aggregated into sessions -- the point is to
-- keep ping-level granularity (timestamp, lat/lng, battery_level, climate
-- fields) available for the drain-attribution analysis and for future joins
-- against external data (e.g. weather by location and time).

CREATE OR REPLACE VIEW silver_battery_state_timeline AS
SELECT
    p.car_id,
    s.state,
    p.drive_id IS NOT NULL AS is_driving,
    EXISTS (
        SELECT 1 FROM teslamate.public.charging_processes cp
        WHERE cp.car_id = p.car_id
          AND p.date >= cp.start_date
          AND (cp.end_date IS NULL OR p.date <= cp.end_date)
    ) AS is_charging,
    p.date,
    p.battery_level,
    p.usable_battery_level,
    p.ideal_battery_range_km,
    p.rated_battery_range_km,
    p.est_battery_range_km,
    p.is_climate_on,
    p.inside_temp,
    p.outside_temp,
    p.driver_temp_setting,
    p.passenger_temp_setting,
    p.battery_heater_on,
    p.speed,
    p.power,
    p.odometer,
    p.drive_id,
    p.latitude,
    p.longitude
FROM teslamate.public.positions p
JOIN teslamate.public.states s
    ON s.car_id = p.car_id
    AND p.date >= s.start_date
    AND (s.end_date IS NULL OR p.date < s.end_date);
