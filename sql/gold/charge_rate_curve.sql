-- Gold: charge_rate_curve
--
-- Charger power at each battery % sample, across all charging sessions.
-- Built from raw per-sample charges pings (not the session-level
-- aggregate) because the whole point is the shape of the curve within a
-- session, not just its start/end.

CREATE OR REPLACE VIEW gold_charge_rate_curve AS
SELECT
    ch.charging_process_id AS charging_session_id,
    cs.car_id,
    cs.car_name,
    ch.date,
    ch.battery_level,
    ch.usable_battery_level,
    ch.charger_power,
    ch.charger_actual_current,
    ch.charger_voltage,
    ch.charger_phases,
    ch.fast_charger_present,
    ch.fast_charger_brand,
    ch.fast_charger_type,
    ch.outside_temp,
    cs.geofence_name,
    cs.address_name
FROM teslamate.public.charges ch
JOIN silver_charging_sessions cs ON cs.charging_session_id = ch.charging_process_id;
