"""DuckDB connection helper: local warehouse + read-only ATTACH to TeslaMate's Postgres.

Safety: the Postgres side is enforced by the `teslamate_ro` role (SELECT-only,
granted at the database level — see CLAUDE.md). READ_ONLY below is a second,
DuckDB-side layer on top of that, not a substitute for it.
"""

import os
from pathlib import Path

import duckdb
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "warehouse.duckdb"


def connect(warehouse_path: Path = WAREHOUSE_PATH) -> duckdb.DuckDBPyConnection:
    load_dotenv(PROJECT_ROOT / ".env")

    host = os.environ["DB_HOST"]
    port = os.environ["DB_PORT"]
    dbname = os.environ["DB_NAME"]
    user = os.environ["DB_USER"]
    password = os.environ["DB_PASSWORD"]

    con = duckdb.connect(str(warehouse_path))
    con.install_extension("postgres")
    con.load_extension("postgres")

    pg_conn_str = (
        f"host={host} port={port} dbname={dbname} user={user} password={password}"
    )
    escaped = pg_conn_str.replace("'", "''")
    con.execute(f"ATTACH '{escaped}' AS teslamate (TYPE POSTGRES, READ_ONLY)")
    return con
