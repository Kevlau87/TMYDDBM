-- Gold: efficiency_vs_conditions
--
-- Per drive segment: how much rated/ideal range was consumed relative to
-- distance actually driven, alongside speed and temperature for that leg.
-- rated_range_efficiency near 1.0 means the drive matched Tesla's own rated
-- range estimate; higher means worse-than-rated, lower means better.
--
-- Deliberately avoids assuming a Wh/km conversion from cars.efficiency --
-- that field's exact semantics aren't confirmed, so this stays in
-- range-km terms, which come straight from the raw pings.

CREATE OR REPLACE VIEW gold_efficiency_vs_conditions AS
SELECT
    drive_id,
    car_id,
    segment_id,
    segment_start,
    segment_end,
    duration_s,
    distance_km,
    avg_speed,
    max_speed,
    avg_outside_temp,
    start_battery_level,
    end_battery_level,
    start_battery_level - end_battery_level AS battery_level_consumed,
    start_rated_range_km - end_rated_range_km AS rated_range_consumed_km,
    start_ideal_range_km - end_ideal_range_km AS ideal_range_consumed_km,
    CASE WHEN distance_km > 0
        THEN (start_rated_range_km - end_rated_range_km) / distance_km
    END AS rated_range_efficiency,
    CASE WHEN distance_km > 0
        THEN (start_ideal_range_km - end_ideal_range_km) / distance_km
    END AS ideal_range_efficiency
FROM silver_drive_segments
WHERE distance_km > 0;
