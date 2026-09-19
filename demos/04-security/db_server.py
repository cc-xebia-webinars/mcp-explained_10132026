"""Two ways to give an AI agent a database, side by side: one risky, one safer.

run_sql hands the model a raw SQL prompt on a read-write connection. Anything the
model writes, or anything a poisoned document persuades it to write, runs as is.

incidents_for_service answers one specific question with a fixed, parameterized
query over a read-only connection. The model only supplies a value, and the
connection itself can't change data even if the query were somehow subverted.

    uv run db_server.py
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import TypedDict

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

import catalog_db
from call_log import ToolCallLog

# Every tool call is recorded in data/tool-calls.log. See call_log.py.
mcp = MCPServer("incidents-db", version="1.0.0", middleware=[ToolCallLog("incidents-db")])


class Incident(TypedDict):
    id: int
    service: str
    title: str
    severity: str
    status: str


# ------------------------------------------------------------------ the risky way

@mcp.tool()
def run_sql(sql: str) -> list[dict]:
    """Run any SQL statement against the incidents database and return the rows."""
    with closing(catalog_db.connect()) as conn, conn:
        cursor = conn.execute(sql)
        if cursor.description is None:
            # Statements such as DELETE return no columns, only a count of changes.
            return [{"rows_changed": cursor.rowcount}]
        return [dict(row) for row in cursor.fetchall()]


# ------------------------------------------------------------------ the safer way

def read_only_connection() -> sqlite3.Connection:
    catalog_db.connect().close()  # creates and seeds the database on first use
    # mode=ro makes SQLite itself refuse writes, so the guarantee doesn't depend on
    # every query in this file being written correctly.
    conn = sqlite3.connect(catalog_db.DB_PATH.as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
def incidents_for_service(service: str) -> list[Incident]:
    """List every incident, open or resolved, for one service, newest first."""
    with closing(read_only_connection()) as conn:
        # The ? placeholder sends the value separately from the SQL text, so a value
        # like "x' OR '1'='1" is just an odd service name that matches nothing.
        rows = conn.execute(
            "SELECT id, service, title, severity, status FROM incidents "
            "WHERE service = ? ORDER BY opened_at DESC",
            (service,),
        ).fetchall()
    return [Incident(**dict(r)) for r in rows]


if __name__ == "__main__":
    mcp.run(transport="stdio")
