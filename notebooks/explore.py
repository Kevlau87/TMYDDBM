import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import altair as alt
    import marimo as mo

    return alt, mo


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
def _(date_range, has_bounds):
    from datetime import datetime, time

    range_start = datetime.combine(date_range.value[0], time.min) if has_bounds else None
    range_end = datetime.combine(date_range.value[1], time.max) if has_bounds else None
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

    `net_elevation_change_m` is surfaced so hill climbs (which cost range for
    reasons that have nothing to do with driving style) can be spotted rather
    than silently skewing the efficiency numbers. Use the slider to exclude
    segments with a large elevation change.
    """)
    return


@app.cell
def _(mo):
    elevation_filter = mo.ui.slider(
        start=0, stop=200, value=200, step=10,
        label="Max |net elevation change| (m)",
    )
    elevation_filter
    return (elevation_filter,)


@app.cell
def _(alt, car_picker, con, elevation_filter, mo, range_end, range_start):
    efficiency_df = con.execute(
        """
        SELECT * FROM gold_efficiency_vs_conditions
        WHERE car_id = ?
          AND segment_start BETWEEN ? AND ?
          AND abs(net_elevation_change_m) <= ?
        ORDER BY segment_start
        """,
        [car_picker.value, range_start, range_end, elevation_filter.value],
    ).df()

    efficiency_chart = (
        mo.ui.altair_chart(
            alt.Chart(efficiency_df)
            .mark_circle(opacity=0.6)
            .encode(
                x=alt.X("avg_outside_temp:Q", title="Avg outside temp (°C)"),
                y=alt.Y(
                    "rated_range_efficiency:Q",
                    title="Rated-range consumed / km driven",
                ),
                size=alt.Size("avg_speed:Q", title="Avg speed"),
                color=alt.Color(
                    "net_elevation_change_m:Q",
                    title="Net elevation change (m)",
                    scale=alt.Scale(scheme="redblue", domainMid=0),
                ),
                tooltip=[
                    "segment_start",
                    "distance_km",
                    "avg_speed",
                    "avg_outside_temp",
                    "rated_range_efficiency",
                    "ascent_m",
                    "descent_m",
                    "net_elevation_change_m",
                ],
            )
            .properties(width=600, height=300)
        )
        if not efficiency_df.empty
        else mo.md("*No completed drive segments in this range yet.*")
    )
    efficiency_chart
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
def _(alt, car_picker, con, mo, range_end, range_start):
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
        _last_points = tire_df.sort_values("date").groupby("tire", as_index=False).tail(1)
        _line = (
            alt.Chart(tire_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("date:T", title="Date"),
                y=alt.Y("pressure:Q", title="Pressure (bar)", scale=alt.Scale(zero=False)),
                color=alt.Color("tire:N", title="Tire", scale=alt.Scale(scheme="tableau10")),
                tooltip=["date", "tire", "pressure"],
            )
        )
        _labels = (
            alt.Chart(_last_points)
            .mark_text(align="left", dx=6, fontSize=11)
            .encode(
                x="date:T",
                y="pressure:Q",
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
                x=alt.X("outside_temp:Q", title="Outside temp (°C)"),
                y=alt.Y("pressure:Q", title="Pressure (bar)", scale=alt.Scale(zero=False)),
                color=alt.Color("tire:N", title="Tire", scale=alt.Scale(scheme="tableau10")),
                tooltip=["date", "tire", "pressure", "outside_temp"],
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
def _(alt, car_picker, con, min_battery_pct, mo, range_end, range_start):
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

    battery_health_chart = (
        mo.ui.altair_chart(
            alt.Chart(battery_health_df)
            .mark_circle(opacity=0.7)
            .encode(
                x=alt.X("end_date:T", title="Charge completed"),
                y=alt.Y(
                    "implied_full_rated_range_km:Q",
                    title="Implied full-charge rated range (km)",
                    scale=alt.Scale(zero=False),
                ),
                tooltip=["end_date", "end_battery_level", "implied_full_rated_range_km"],
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
