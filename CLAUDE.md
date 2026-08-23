# TMYDDBM — Tesla Model Y DuckDB/Marimo

Personal analytics project on my own Tesla Model Y's telemetry: charging
behavior, discharge/usage events, and how driving conditions affect battery %.
This is a learning project — the goal is practicing DuckDB and Marimo for
interactive data analysis, not building a production system.

## Scope boundary — read this first

**TeslaMate itself is out of scope for this project.** TeslaMate is
self-hosted separately (Docker, polls the Tesla Owner API, writes to
Postgres). Its docker-compose file and credentials live outside this
project's working directory.

- Do not manage, configure, or modify the TeslaMate deployment.
- Treat TeslaMate's Postgres database as an external system this project
  only *reads from*.
- If a task seems to require write access to TeslaMate's database, or
  changes to the TeslaMate deployment itself, stop and flag it instead of
  proceeding — it belongs in a different project.

## Non-negotiable safety constraint

**This project must only ever connect to Postgres using the read-only role
`teslamate_ro`** (`SELECT` privileges only — no `DROP`/`TRUNCATE`/`DELETE`/
`ALTER`/`INSERT`/`UPDATE`). This is enforced at the database level, not by
convention:

- Never write, suggest, or run SQL against the TeslaMate database using any
  role other than `teslamate_ro`.
- Never write code that modifies, migrates, or deletes TeslaMate's schema or
  data.
- All analysis output (silver/gold tables, session detections, derived
  metrics) lives in DuckDB's own local storage (`data/warehouse.duckdb`),
  never written back into TeslaMate's Postgres.

## Tech stack

- Python (3.13, managed with `uv`)
- DuckDB, using the `postgres` extension to `ATTACH` TeslaMate's Postgres
  read-only — not a second synced copy of the data
- Marimo, plain `.py` notebooks (git-diffable), reactive
- No web framework, no auth, no deployment tooling — local and single-user

## Architecture — medallion layering in DuckDB

- **Bronze**: TeslaMate's existing Postgres tables, read as-is via the
  `ATTACH`ed connection. No transformation, no copy.
- **Silver**: SQL views/tables in DuckDB that detect session boundaries and
  normalize the raw snapshot stream into `charging_sessions` and
  `drive_segments`.
- **Gold**: derived analytical views — efficiency vs. temperature/speed,
  charge-rate-vs-% curves, drain attribution.

## Known hard problem (not a bug)

TeslaMate/Tesla's data has no field labeling *why* battery dropped (climate
vs. driving vs. phantom drain). This must be derived by correlating
state-change deltas against battery-level deltas over time. Treat this as
the core interesting problem of the project — don't shortcut it with
assumptions.

## Explicit non-goals for v1

- No external traffic API. If a proxy for traffic is needed later, it's
  speed-variance from GPS points already in the data — not now.
- No deployment/uptime concerns — running locally only.

## Schema notes

TeslaMate's actual table/column names should be confirmed via
`information_schema` through the read-only connection, not assumed from
memory — names may not match upstream TeslaMate docs exactly (version
drift, migrations, etc.). Once introspected, notes should be added here or
in `sql/` comments.

## Build phases

See project chat history / PR descriptions for the phased plan. Roughly:
Phase 1 (ATTACH + read access + row-count sanity check) → Phase 2 (silver
session-boundary detection) → Phase 3 (gold analytical views) → Phase 4
(Marimo notebook) → Phase 5 (marimo pair for open-ended querying, later).
Build one phase at a time; don't jump ahead without approval.
