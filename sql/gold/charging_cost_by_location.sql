-- Gold: charging_cost_by_location
--
-- Rolls up charging sessions by location (geofence name, falling back to
-- address, falling back to "Unknown"). Cost accuracy depends entirely on
-- whatever per-kWh rates are configured inside TeslaMate itself -- that
-- config lives outside this project's scope, so treat cost as only as
-- trustworthy as that setup.

CREATE OR REPLACE VIEW gold_charging_cost_by_location AS
SELECT
    car_id,
    COALESCE(geofence_name, address_name, 'Unknown') AS location,
    count(*) AS session_count,
    sum(charge_energy_added) AS total_energy_added_kwh,
    sum(cost) AS total_cost,
    CASE WHEN sum(charge_energy_added) > 0
        THEN sum(cost) / sum(charge_energy_added)
    END AS avg_cost_per_kwh,
    min(start_date) AS first_session,
    max(end_date) AS last_session
FROM silver_charging_sessions
GROUP BY car_id, COALESCE(geofence_name, address_name, 'Unknown');
