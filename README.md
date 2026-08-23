# TMYDDBM

Personal analytics on my own Tesla Model Y's telemetry — charging behavior,
discharge/usage events, and how driving conditions affect battery %. It's a
learning project: the point is practicing [DuckDB](https://duckdb.org/) and
[Marimo](https://marimo.io/) for interactive data analysis, not building a
production system.

## How it fits together

- **[TeslaMate](https://github.com/teslamate-org/teslamate)** — self-hosted
  separately (Docker), polls the Tesla Owner API and writes to Postgres.
  Not part of this repo; treated as a read-only external system.
- **DuckDB** — embedded, zero-ops query layer. `ATTACH`es TeslaMate's
  Postgres directly (via the `postgres` extension) and queries it live —
  there's no separate synced copy of the data.
- **Marimo** — reactive Python notebooks (plain `.py`, git-diffable) for the
  interactive/exploratory layer, reading the derived views below.

Data flows through a medallion-style layering, all inside one local DuckDB
file (`data/warehouse.duckdb`):

- **Bronze** — TeslaMate's Postgres tables, read as-is through the `ATTACH`.
- **Silver** (`sql/silver/`) — normalized views: `silver_charging_sessions`,
  `silver_drive_segments`, and `silver_battery_state_timeline` (every
  position ping matched to its driving/charging/parked/asleep state — the
  raw material for drain attribution).
- **Gold** (`sql/gold/`) — derived analytical views: efficiency vs.
  temperature/speed, charge-rate-vs-% curves, drain attribution.

### The interesting problem

Neither Tesla's API nor TeslaMate labels *why* the battery dropped — climate
running, actually driving, or just phantom drain while parked. That has to
be derived by correlating state-change deltas against battery-level deltas
over time. That's the core problem this project is built to explore, not
something to shortcut with assumptions.

## Safety constraint

This project only ever connects to TeslaMate's Postgres using a **read-only**
role (`teslamate_ro` — `SELECT` only, no `DROP`/`TRUNCATE`/`DELETE`/`ALTER`),
enforced at the database level and again by DuckDB's `READ_ONLY` attach mode.
All derived output lives in this project's own local DuckDB file, never
written back to TeslaMate.

See [CLAUDE.md](CLAUDE.md) for the full set of constraints this project
operates under.

## Layout

```
sql/silver/     SQL views: session normalization, battery-state timeline
sql/gold/       SQL views: derived analytical metrics (WIP)
src/tmyddbm/    Python: connection helper, silver/gold view builder
notebooks/      Marimo notebooks (WIP)
data/           Local DuckDB warehouse file (gitignored)
```

## Setup

Requires a running TeslaMate instance and a `teslamate_ro` Postgres role.

```
uv sync
cp .env.example .env   # fill in DB_HOST/PORT/NAME/USER/PASSWORD
uv run python -m tmyddbm.transforms   # builds silver/gold views
```

## Status

Silver layer (session normalization + battery-state timeline) is built and
verified against a live TeslaMate instance. Gold-layer analytical views and
the Marimo notebook are next.
