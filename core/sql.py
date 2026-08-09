"""In-memory SQL engine so analysts can query DataFrames with real SQL."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

import pandas as pd

FORBIDDEN = re.compile(r"\b(attach|detach|pragma|vacuum)\b", re.IGNORECASE)


@dataclass
class SQLResult:
    frame: pd.DataFrame | None
    message: str
    ok: bool = True


class SQLEngine:
    """Loads DataFrames into an ephemeral SQLite database and runs queries."""

    def __init__(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.tables: dict[str, int] = {}

    def register(self, name: str, df: pd.DataFrame) -> None:
        safe = re.sub(r"\W+", "_", name).strip("_") or "data"
        frame = df.copy()
        for col in frame.columns:
            if str(frame[col].dtype) == "category":
                frame[col] = frame[col].astype(str)
        frame.to_sql(safe, self.conn, if_exists="replace", index=False)
        self.tables[safe] = len(frame)

    def list_tables(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows]

    def schema(self, table: str) -> pd.DataFrame:
        try:
            info = self.conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        except sqlite3.Error as exc:
            return pd.DataFrame({"error": [str(exc)]})
        return pd.DataFrame([{"column": r[1], "type": r[2]} for r in info])

    def execute(self, query: str, limit: int = 5000) -> SQLResult:
        text = (query or "").strip().rstrip(";")
        if not text:
            return SQLResult(None, "Enter a SQL statement.", False)
        if FORBIDDEN.search(text):
            return SQLResult(None, "This statement is not allowed in the SQL console.", False)
        try:
            if text.lower().startswith(("select", "with")):
                frame = pd.read_sql_query(text, self.conn)
                if limit and len(frame) > limit:
                    frame = frame.head(limit)
                    return SQLResult(frame, f"Returned first {limit:,} rows.")
                return SQLResult(frame, f"{len(frame):,} row(s) returned.")
            cursor = self.conn.execute(text)
            self.conn.commit()
            return SQLResult(None, f"Statement executed ({cursor.rowcount} row(s) affected).")
        except Exception as exc:
            return SQLResult(None, str(exc), False)

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:  # pragma: no cover
            pass


def run_query(df: pd.DataFrame, query: str, table: str = "data") -> SQLResult:
    """Convenience helper: one-shot query against a single DataFrame."""
    engine = SQLEngine()
    try:
        engine.register(table, df)
        return engine.execute(query)
    finally:
        engine.close()
