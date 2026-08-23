-- Silver: drive_segments
--
-- One row per contiguous "moving" leg within a TeslaMate drive, split on
-- stops longer than STOP_GAP_SECONDS. TeslaMate's `drives` table gives one
-- row per whole trip; this breaks a trip into legs around traffic stops /
-- red lights, which is what the speed-vs-efficiency gold view needs.
--
-- Position-level fields (lat/lng, timestamps) are preserved per segment so
-- this can still be joined against external data (e.g. weather-by-location-
-- and-time) later without going back to raw positions.

CREATE OR REPLACE VIEW silver_drive_segments AS
WITH ordered_positions AS (
    SELECT
        p.*,
        d.car_id,
        LAG(p.date) OVER (PARTITION BY p.drive_id ORDER BY p.date) AS prev_date,
        LAG(p.speed) OVER (PARTITION BY p.drive_id ORDER BY p.date) AS prev_speed
    FROM teslamate.public.positions p
    JOIN teslamate.public.drives d ON d.id = p.drive_id
    WHERE p.drive_id IS NOT NULL
),
flagged AS (
    SELECT
        *,
        CASE
            WHEN prev_date IS NULL THEN 1
            WHEN speed = 0 AND prev_speed = 0
                 AND date_diff('second', prev_date, date) > 120 THEN 1
            ELSE 0
        END AS is_new_segment
    FROM ordered_positions
),
segmented AS (
    SELECT
        *,
        SUM(is_new_segment) OVER (
            PARTITION BY drive_id ORDER BY date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS segment_id
    FROM flagged
),
with_elevation_delta AS (
    SELECT
        *,
        elevation - LAG(elevation) OVER (
            PARTITION BY drive_id, segment_id ORDER BY date
        ) AS elevation_delta_m
    FROM segmented
)
SELECT
    drive_id,
    car_id,
    segment_id,
    min(date) AS segment_start,
    max(date) AS segment_end,
    date_diff('second', min(date), max(date)) AS duration_s,
    arg_min(battery_level, date) AS start_battery_level,
    arg_max(battery_level, date) AS end_battery_level,
    arg_min(rated_battery_range_km, date) AS start_rated_range_km,
    arg_max(rated_battery_range_km, date) AS end_rated_range_km,
    arg_min(ideal_battery_range_km, date) AS start_ideal_range_km,
    arg_max(ideal_battery_range_km, date) AS end_ideal_range_km,
    avg(speed) AS avg_speed,
    max(speed) AS max_speed,
    avg(outside_temp) AS avg_outside_temp,
    avg(power) AS avg_power,
    min(odometer) AS start_odometer,
    max(odometer) AS end_odometer,
    max(odometer) - min(odometer) AS distance_km,
    arg_min(latitude, date) AS start_lat,
    arg_min(longitude, date) AS start_lng,
    arg_max(latitude, date) AS end_lat,
    arg_max(longitude, date) AS end_lng,
    sum(GREATEST(elevation_delta_m, 0)) AS ascent_m,
    sum(GREATEST(-elevation_delta_m, 0)) AS descent_m,
    arg_max(elevation, date) - arg_min(elevation, date) AS net_elevation_change_m,
    count(*) AS position_count
FROM with_elevation_delta
GROUP BY drive_id, car_id, segment_id;
