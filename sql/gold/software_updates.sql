-- Gold: software_updates
--
-- Update install history, meant to be overlaid as markers on the
-- efficiency/drain time-series charts -- shifts in behavior that line up
-- with an update boundary are a lot more explainable than ones that don't.

CREATE OR REPLACE VIEW gold_software_updates AS
SELECT
    u.id AS update_id,
    u.car_id,
    c.name AS car_name,
    u.version,
    u.start_date,
    u.end_date,
    date_diff('minute', u.start_date, u.end_date) AS install_duration_min
FROM teslamate.public.updates u
JOIN teslamate.public.cars c ON c.id = u.car_id;
