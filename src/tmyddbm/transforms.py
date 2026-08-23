"""Applies the SQL files in sql/ as views in the local DuckDB warehouse.

Silver/gold layers are views over the ATTACHed Postgres connection, not
materialized copies -- there's nothing to "refresh," just re-run this after
editing a .sql file to pick up the new definition.
"""

from pathlib import Path

import duckdb

from tmyddbm.db import PROJECT_ROOT, connect

SILVER_DIR = PROJECT_ROOT / "sql" / "silver"
GOLD_DIR = PROJECT_ROOT / "sql" / "gold"


def _apply_dir(con: duckdb.DuckDBPyConnection, sql_dir: Path) -> None:
    for sql_file in sorted(sql_dir.glob("*.sql")):
        con.execute(sql_file.read_text())


def build_silver(con: duckdb.DuckDBPyConnection) -> None:
    _apply_dir(con, SILVER_DIR)


def build_gold(con: duckdb.DuckDBPyConnection) -> None:
    _apply_dir(con, GOLD_DIR)


if __name__ == "__main__":
    con = connect()
    build_silver(con)
    build_gold(con)
    print("silver/gold views (re)built")
