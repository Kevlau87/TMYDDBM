import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import altair as alt
    import marimo as mo

    from tmyddbm.units import bar_to_psi, c_to_f, ft_to_m, km_to_mi, kmh_to_mph, m_to_ft

    return alt, bar_to_psi, c_to_f, ft_to_m, km_to_mi, kmh_to_mph, m_to_ft, mo


@app.cell
def _():
    from tmyddbm.db import connect
    from tmyddbm.transforms import build_gold, build_silver

    con = connect()
    build_silver(con)
    build_gold(con)
    return (con,)


@app.cell
def _(con, mo):
    cars_df = con.execute(
        "SELECT id, name, model FROM teslamate.public.cars ORDER BY id"
    ).df()
    car_names = {row.id: (row.name or row.model) for row in cars_df.itertuples()}
    car_options = {f"{name} (#{cid})": cid for cid, name in car_names.items()}
    car_picker = mo.ui.dropdown(
        options=car_options,
        value=next(iter(car_options), None),
        label="Car",
    )
    car_picker
    return car_names, car_picker


@app.cell
def _(car_names, car_picker, mo):
    mo.md(f"""
    # {car_names.get(car_picker.value, 'Tesla')} — telemetry explorer
    """)
    return


@app.cell
def _(mo):
    refresh_button = mo.ui.refresh(
        options=["10s", "30s", "1m", "2m", "5m"],
        default_interval="30s",
        label="Auto-refresh",
    )
    refresh_button
    return (refresh_button,)


@app.cell
def _(mo):
    auto_extend = mo.ui.checkbox(
        value=True,
        label="Auto-extend end date to latest data",
    )
    auto_extend
    return (auto_extend,)


@app.cell
def _(con, mo):
    date_bounds = con.execute(
        "SELECT min(date), max(date) FROM teslamate.public.positions"
    ).fetchone()
    has_bounds = date_bounds[0] is not None
    date_range = mo.ui.date_range(
        start=date_bounds[0].date() if has_bounds else None,
        stop=date_bounds[1].date() if has_bounds else None,
        value=(date_bounds[0].date(), date_bounds[1].date()) if has_bounds else None,
        label="Date range",
    )
    date_range
    return date_range, has_bounds


@app.cell
def _(auto_extend, con, date_range, has_bounds, refresh_button):
    from datetime import datetime, time

    _ = refresh_button.value  # re-run this cell (and everything downstream) on each tick

    range_start = datetime.combine(date_range.value[0], time.min) if has_bounds else None

    if has_bounds and auto_extend.value:
        _latest = con.execute("SELECT max(date) FROM teslamate.public.positions").fetchone()[0]
        range_end = _latest
    elif has_bounds:
        range_end = datetime.combine(date_range.value[1], time.max)
    else:
        range_end = None
    return range_end, range_start


@app.cell
def _(mo):
    mo.md("""
    ## Charge rate vs battery %

    Power tapers down as battery % rises -- that's the charger protecting the
    battery near full, not a bug. Each line is one charging session, traced in
    chronological order so the taper reads as a curve.
    """)
    return


@app.cell
def _(alt, car_picker, con, mo, range_end, range_start):
    charge_df = con.execute(
        """
        SELECT * FROM gold_charge_rate_curve
        WHERE car_id = ?
          AND date BETWEEN ? AND ?
        ORDER BY date
        """,
        [car_picker.value, range_start, range_end],
    ).df()

    charge_chart = (
        mo.ui.altair_chart(
            alt.Chart(charge_df)
            .mark_line(point=True, strokeWidth=2)
            .encode(
                x=alt.X("battery_level:Q", title="Battery %"),
                y=alt.Y("charger_power:Q", title="Charger power (kW)"),
                order=alt.Order("date:T"),
                color=alt.Color(
                    "charging_session_id:N",
                    title="Session",
                    scale=alt.Scale(scheme="tableau10"),
                ),
                tooltip=[
                    "date",
                    "battery_level",
                    "charger_power",
                    "fast_charger_brand",
                ],
            )
            .properties(width=600, height=300)
        )
        if not charge_df.empty
        else mo.md("*No charging sessions in this range yet.*")
    )
    charge_chart
    return


@app.cell
def _(mo):
    mo.md("""
    ## Efficiency vs outside temperature

    Net elevation change is surfaced so hill climbs (which cost range for
    reasons that have nothing to do with driving style) can be spotted rather
    than silently skewing the efficiency numbers. Use the slider to exclude
    segments with a large elevation change.
    """)
    return


@app.cell
def _(mo):
    elevation_filter = mo.ui.slider(
        start=0, stop=650, value=650, step=25,
        label="Max |net elevation change| (ft)",
    )
    elevation_filter
    return (elevation_filter,)


@app.cell
def _(
    alt,
    c_to_f,
    car_picker,
    con,
    elevation_filter,
    ft_to_m,
    km_to_mi,
    kmh_to_mph,
    m_to_ft,
    mo,
    range_end,
    range_start,
):
    efficiency_df = con.execute(
        """
        SELECT * FROM gold_efficiency_vs_conditions
        WHERE car_id = ?
          AND segment_start BETWEEN ? AND ?
          AND abs(net_elevation_change_m) <= ?
        ORDER BY segment_start
        """,
        [car_picker.value, range_start, range_end, ft_to_m(elevation_filter.value)],
    ).df()

    if not efficiency_df.empty:
        efficiency_df["distance_mi"] = km_to_mi(efficiency_df["distance_km"])
        efficiency_df["avg_speed_mph"] = kmh_to_mph(efficiency_df["avg_speed"])
        efficiency_df["avg_outside_temp_f"] = c_to_f(efficiency_df["avg_outside_temp"])
        efficiency_df["ascent_ft"] = m_to_ft(efficiency_df["ascent_m"])
        efficiency_df["descent_ft"] = m_to_ft(efficiency_df["descent_m"])
        efficiency_df["net_elevation_change_ft"] = m_to_ft(efficiency_df["net_elevation_change_m"])

    efficiency_chart = (
        mo.ui.altair_chart(
            alt.Chart(efficiency_df)
            .mark_circle(opacity=0.6)
            .encode(
                x=alt.X("avg_outside_temp_f:Q", title="Avg outside temp (\u00b0F)"),
                y=alt.Y(
                    "rated_range_efficiency:Q",
                    title="Rated-range consumed / mile driven",
                ),
                size=alt.Size("avg_speed_mph:Q", title="Avg speed (mph)"),
                color=alt.Color(
                    "net_elevation_change_ft:Q",
                    title="Net elevation change (ft)",
                    scale=alt.Scale(scheme="redblue", domainMid=0),
                ),
                tooltip=[
                    "segment_start",
                    "distance_mi",
                    "avg_speed_mph",
                    "avg_outside_temp_f",
                    "rated_range_efficiency",
                    "ascent_ft",
                    "descent_ft",
                    "net_elevation_change_ft",
                ],
            )
            .properties(width=600, height=300)
        )
        if not efficiency_df.empty
        else mo.md("*No completed drive segments in this range yet.*")
    )
    efficiency_chart
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Drive summary

    Distance, duration, speed, and elevation change per drive leg (legs split
    on stops longer than two minutes -- see silver_drive_segments).
    """)
    return


@app.cell
def _(
    c_to_f,
    car_picker,
    con,
    km_to_mi,
    kmh_to_mph,
    m_to_ft,
    mo,
    range_end,
    range_start,
):
    drive_summary_df = con.execute(
        """
        SELECT
            drive_id,
            segment_id,
            segment_start,
            segment_end,
            duration_s,
            distance_km,
            avg_speed,
            max_speed,
            ascent_m,
            descent_m,
            avg_outside_temp
        FROM silver_drive_segments
        WHERE car_id = ?
          AND segment_start BETWEEN ? AND ?
        ORDER BY segment_start DESC
        """,
        [car_picker.value, range_start, range_end],
    ).df()

    if not drive_summary_df.empty:
        drive_summary_df = drive_summary_df.assign(
            distance_mi=km_to_mi(drive_summary_df["distance_km"]).round(2),
            avg_speed_mph=kmh_to_mph(drive_summary_df["avg_speed"]).round(1),
            max_speed_mph=kmh_to_mph(drive_summary_df["max_speed"]).round(1),
            ascent_ft=m_to_ft(drive_summary_df["ascent_m"]).round(0),
            descent_ft=m_to_ft(drive_summary_df["descent_m"]).round(0),
            avg_outside_temp_f=c_to_f(drive_summary_df["avg_outside_temp"]).round(1),
        ).drop(columns=["distance_km", "avg_speed", "max_speed", "ascent_m", "descent_m", "avg_outside_temp"])
        drive_summary_df = drive_summary_df.rename(columns={
            "drive_id": "Drive",
            "segment_id": "Segment",
            "segment_start": "Start",
            "segment_end": "End",
            "duration_s": "Duration (s)",
            "distance_mi": "Distance (mi)",
            "avg_speed_mph": "Avg speed (mph)",
            "max_speed_mph": "Max speed (mph)",
            "ascent_ft": "Ascent (ft)",
            "descent_ft": "Descent (ft)",
            "avg_outside_temp_f": "Avg outside temp (\u00b0F)",
        })

    drive_summary_table = (
        mo.ui.table(drive_summary_df)
        if not drive_summary_df.empty
        else mo.md("*No completed drives in this range yet.*")
    )
    drive_summary_table
    return


@app.cell
def _(mo):
    mo.md("""
    ## Battery drain by category

    Signed battery % change per category, relative to zero -- bars below zero
    added charge (charging), bars above zero consumed it (driving, phantom
    drain while parked).
    """)
    return


@app.cell
def _(alt, car_picker, con, mo, range_end, range_start):
    drain_df = con.execute(
        """
        SELECT * FROM gold_drain_attribution
        WHERE car_id = ?
          AND interval_start BETWEEN ? AND ?
        ORDER BY interval_start
        """,
        [car_picker.value, range_start, range_end],
    ).df()

    drain_summary = (
        drain_df.groupby("drain_category", as_index=False)["battery_level_drop"].sum()
        if not drain_df.empty
        else drain_df
    )

    drain_chart = (
        mo.ui.altair_chart(
            alt.Chart(drain_summary)
            .mark_bar()
            .encode(
                x=alt.X("drain_category:N", title="Category", sort="-y"),
                y=alt.Y(
                    "battery_level_drop:Q",
                    title="Battery % change (negative = added charge)",
                ),
                color=alt.Color(
                    "battery_level_drop:Q",
                    scale=alt.Scale(scheme="redblue", domainMid=0),
                    legend=None,
                ),
            )
            .properties(width=500, height=300)
        )
        if not drain_summary.empty
        else mo.md("*No timeline data in this range yet.*")
    )
    drain_chart
    return


@app.cell
def _(mo):
    mo.md("""
    ## Tire pressure over time

    Pressure per tire, most recent day first. Cold weather also drops pressure
    measurably -- that relationship (below) will get more informative as more
    of a temperature range gets logged; right now there's only one day's worth.
    """)
    return


@app.cell
def _(alt, bar_to_psi, c_to_f, car_picker, con, mo, range_end, range_start):
    tire_df = con.execute(
        """
        SELECT * FROM gold_tire_pressure_trends
        WHERE car_id = ?
          AND date BETWEEN ? AND ?
        ORDER BY date
        """,
        [car_picker.value, range_start, range_end],
    ).df()

    if not tire_df.empty:
        tire_df["pressure_psi"] = bar_to_psi(tire_df["pressure"])
        tire_df["outside_temp_f"] = c_to_f(tire_df["outside_temp"])

        _last_points = tire_df.sort_values("date").groupby("tire", as_index=False).tail(1)
        _line = (
            alt.Chart(tire_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("date:T", title="Date"),
                y=alt.Y("pressure_psi:Q", title="Pressure (psi)", scale=alt.Scale(zero=False)),
                color=alt.Color("tire:N", title="Tire", scale=alt.Scale(scheme="tableau10")),
                tooltip=["date", "tire", "pressure_psi"],
            )
        )
        _labels = (
            alt.Chart(_last_points)
            .mark_text(align="left", dx=6, fontSize=11)
            .encode(
                x="date:T",
                y="pressure_psi:Q",
                color=alt.Color("tire:N", legend=None, scale=alt.Scale(scheme="tableau10")),
                text="tire:N",
            )
        )
        tire_pressure_over_time_chart = mo.ui.altair_chart(
            (_line + _labels).properties(width=650, height=300)
        )
    else:
        tire_pressure_over_time_chart = mo.md("*No tire pressure readings in this range yet.*")
    tire_pressure_over_time_chart
    return (tire_df,)


@app.cell
def _(alt, mo, tire_df):
    tire_pressure_vs_temp_chart = (
        mo.ui.altair_chart(
            alt.Chart(tire_df)
            .mark_circle(opacity=0.5)
            .encode(
                x=alt.X("outside_temp_f:Q", title="Outside temp (\u00b0F)"),
                y=alt.Y("pressure_psi:Q", title="Pressure (psi)", scale=alt.Scale(zero=False)),
                color=alt.Color("tire:N", title="Tire", scale=alt.Scale(scheme="tableau10")),
                tooltip=["date", "tire", "pressure_psi", "outside_temp_f"],
            )
            .properties(width=600, height=300)
        )
        if not tire_df.empty
        else mo.md("*No tire pressure readings in this range yet.*")
    )
    tire_pressure_vs_temp_chart
    return


@app.cell
def _(mo):
    mo.md("""
    ## Charging cost by location

    Cost accuracy depends on the per-kWh rates configured inside TeslaMate
    itself -- that's outside this project's scope, so treat this as only as
    trustworthy as that setup.
    """)
    return


@app.cell
def _(car_picker, con, mo):
    cost_by_location_df = con.execute(
        """
        SELECT * FROM gold_charging_cost_by_location
        WHERE car_id = ?
        ORDER BY total_cost DESC NULLS LAST
        """,
        [car_picker.value],
    ).df()

    cost_by_location_table = (
        mo.ui.table(cost_by_location_df)
        if not cost_by_location_df.empty
        else mo.md("*No charging sessions yet.*")
    )
    cost_by_location_table
    return


@app.cell
def _(mo):
    mo.md("""
    ## Battery health (degradation proxy)

    Rated/ideal range at charge completion, extrapolated to what it would
    imply at a full 100% charge. Higher end-of-charge % sessions are more
    trustworthy extrapolations -- use the slider to require a higher floor.
    """)
    return


@app.cell
def _(mo):
    min_battery_pct = mo.ui.slider(
        start=0, stop=100, value=50, step=5,
        label="Min end battery % (for reliability)",
    )
    min_battery_pct
    return (min_battery_pct,)


@app.cell
def _(
    alt,
    car_picker,
    con,
    km_to_mi,
    min_battery_pct,
    mo,
    range_end,
    range_start,
):
    battery_health_df = con.execute(
        """
        SELECT * FROM gold_battery_health
        WHERE car_id = ?
          AND end_date BETWEEN ? AND ?
          AND end_battery_level >= ?
        ORDER BY end_date
        """,
        [car_picker.value, range_start, range_end, min_battery_pct.value],
    ).df()

    if not battery_health_df.empty:
        battery_health_df["implied_full_rated_range_mi"] = km_to_mi(
            battery_health_df["implied_full_rated_range_km"]
        )

    battery_health_chart = (
        mo.ui.altair_chart(
            alt.Chart(battery_health_df)
            .mark_circle(opacity=0.7)
            .encode(
                x=alt.X("end_date:T", title="Charge completed"),
                y=alt.Y(
                    "implied_full_rated_range_mi:Q",
                    title="Implied full-charge rated range (mi)",
                    scale=alt.Scale(zero=False),
                ),
                tooltip=["end_date", "end_battery_level", "implied_full_rated_range_mi"],
            )
            .properties(width=600, height=300)
        )
        if not battery_health_df.empty
        else mo.md("*No qualifying charge sessions in this range yet.*")
    )
    battery_health_chart
    return


@app.cell
def _(mo):
    mo.md("""
    ## Software update history
    """)
    return


@app.cell
def _(car_picker, con, mo):
    updates_df = con.execute(
        """
        SELECT version, start_date, end_date, install_duration_min
        FROM gold_software_updates
        WHERE car_id = ?
        ORDER BY start_date DESC
        """,
        [car_picker.value],
    ).df()

    updates_table = (
        mo.ui.table(updates_df)
        if not updates_df.empty
        else mo.md("*No update history yet.*")
    )
    updates_table
    return


if __name__ == "__main__":
    app.run()
