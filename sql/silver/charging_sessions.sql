-- Silver: charging_sessions
--
-- TeslaMate already detects charging session boundaries itself (that's what
-- charging_processes is). This is a normalization pass -- car/location names
-- joined in -- not a re-detection of boundaries.

CREATE OR REPLACE VIEW silver_charging_sessions AS
SELECT
    cp.id AS charging_session_id,
    cp.car_id,
    c.name AS car_name,
    c.model AS car_model,
    cp.start_date,
    cp.end_date,
    cp.duration_min,
    cp.start_battery_level,
    cp.end_battery_level,
    cp.end_battery_level - cp.start_battery_level AS battery_level_delta,
    cp.start_rated_range_km,
    cp.end_rated_range_km,
    cp.start_ideal_range_km,
    cp.end_ideal_range_km,
    cp.charge_energy_added,
    cp.charge_energy_used,
    cp.cost,
    cp.outside_temp_avg,
    cp.position_id,
    cp.address_id,
    a.display_name AS address_name,
    a.latitude AS address_lat,
    a.longitude AS address_lng,
    cp.geofence_id,
    g.name AS geofence_name
FROM teslamate.public.charging_processes cp
JOIN teslamate.public.cars c ON c.id = cp.car_id
LEFT JOIN teslamate.public.addresses a ON a.id = cp.address_id
LEFT JOIN teslamate.public.geofences g ON g.id = cp.geofence_id;
