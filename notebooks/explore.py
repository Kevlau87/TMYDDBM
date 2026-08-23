import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import altair as alt
    import marimo as mo

    return alt, mo


@app.cell
def _(mo):
    mo.md("# Tesla telemetry explorer")
    return


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
    car_options = {
        f"{(row.name or row.model)} (#{row.id})": row.id
        for row in cars_df.itertuples()
    }
    car_picker = mo.ui.dropdown(
        options=car_options,
        value=next(iter(car_options), None),
        label="Car",
    )
    car_picker
    return (car_picker,)


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
    return (date_range,)


@app.cell
def _(mo):
    mo.md("## Charge rate vs battery %")
    return


@app.cell
def _(alt, car_picker, con, date_range, mo):
    charge_df = con.execute(
        """
        SELECT * FROM gold_charge_rate_curve
        WHERE car_id = ?
          AND date BETWEEN ? AND ?
        ORDER BY date
        """,
        [car_picker.value, date_range.value[0], date_range.value[1]],
    ).df()

    charge_chart = (
        mo.ui.altair_chart(
            alt.Chart(charge_df)
            .mark_circle(opacity=0.6)
            .encode(
                x=alt.X("battery_level:Q", title="Battery %"),
                y=alt.Y("charger_power:Q", title="Charger power (kW)"),
                color=alt.Color("charging_session_id:N", legend=None),
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
    mo.md("## Efficiency vs outside temperature")
    return


@app.cell
def _(alt, car_picker, con, date_range, mo):
    efficiency_df = con.execute(
        """
        SELECT * FROM gold_efficiency_vs_conditions
        WHERE car_id = ?
          AND segment_start BETWEEN ? AND ?
        ORDER BY segment_start
        """,
        [car_picker.value, date_range.value[0], date_range.value[1]],
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
                tooltip=[
                    "segment_start",
                    "distance_km",
                    "avg_speed",
                    "avg_outside_temp",
                    "rated_range_efficiency",
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
    mo.md("## Battery drain by category")
    return


@app.cell
def _(alt, car_picker, con, date_range, mo):
    drain_df = con.execute(
        """
        SELECT * FROM gold_drain_attribution
        WHERE car_id = ?
          AND interval_start BETWEEN ? AND ?
        ORDER BY interval_start
        """,
        [car_picker.value, date_range.value[0], date_range.value[1]],
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
                x=alt.X("drain_category:N", title="Category"),
                y=alt.Y("battery_level_drop:Q", title="Total battery % consumed"),
                color=alt.Color("drain_category:N", legend=None),
            )
            .properties(width=500, height=300)
        )
        if not drain_summary.empty
        else mo.md("*No timeline data in this range yet.*")
    )
    drain_chart
    return


if __name__ == "__main__":
    app.run()
