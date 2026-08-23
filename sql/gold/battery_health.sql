-- Gold: battery_health
--
-- Degradation proxy: rated/ideal range at charge completion, extrapolated
-- to what it would imply at a full 100% charge (range / (battery% / 100)).
-- This assumes rated range scales roughly linearly with battery % near the
-- session's actual end level -- true enough to be useful, not exact at the
-- extremes. Every session is included with its own end_battery_level so
-- the notebook can filter to higher-confidence (higher %) sessions with a
-- slider rather than a threshold hardcoded here.

CREATE OR REPLACE VIEW gold_battery_health AS
SELECT
    charging_session_id,
    car_id,
    car_name,
    end_date,
    end_battery_level,
    end_rated_range_km,
    end_ideal_range_km,
    CASE WHEN end_battery_level > 0
        THEN end_rated_range_km / (end_battery_level / 100.0)
    END AS implied_full_rated_range_km,
    CASE WHEN end_battery_level > 0
        THEN end_ideal_range_km / (end_battery_level / 100.0)
    END AS implied_full_ideal_range_km
FROM silver_charging_sessions
WHERE end_battery_level IS NOT NULL AND end_battery_level > 0;
