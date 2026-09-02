"""Least-privilege SQLAlchemy connector for supported DataSense database sources."""
from __future__ import annotations

import re

import pandas as pd
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import URL

_READ_ONLY = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
_BLOCKED = re.compile(r"\b(attach|detach|pragma|vacuum|insert|update|delete|drop|alter|create|replace|truncate|grant|revoke|call|copy)\b", re.IGNORECASE)


class DBConnector:
    """Database connector constrained to read-only analytics by default."""

    def __init__(self, *, read_only: bool = True, query_limit: int = 5000):
        self.engine = None
        self.read_only = read_only
        self.query_limit = query_limit

    @staticmethod
    def _connection_url(db_type: str, host: str, port: int | str, user: str, password: str, database: str) -> URL:
        if db_type == "MySQL":
            return URL.create("mysql+mysqlconnector", username=user, password=password, host=host, port=int(port), database=database)
        if db_type == "PostgreSQL":
            return URL.create("postgresql+psycopg2", username=user, password=password, host=host, port=int(port), database=database)
        if db_type == "SQLite":
            return URL.create("sqlite", database=database)
        raise ValueError("Unsupported database type.")

    def connect(self, db_type, host, port, user, password, database):
        try:
            url = self._connection_url(db_type, host, port, user, password, database)
            self.engine = create_engine(url, pool_pre_ping=True)
            with self.engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            return True, "Connection established."
        except Exception as exc:
            self.engine = None
            return False, str(exc)

    def execute_query(self, query: str, limit: int | None = None):
        if self.engine is None:
            return None, "Connect to a database first."
        text = (query or "").strip().rstrip(";")
        if not _READ_ONLY.match(text):
            return None, "Only read-only SELECT/WITH queries are allowed by this connector."
        if _BLOCKED.search(text):
            return None, "The query contains a blocked database operation."
        try:
            frame = pd.read_sql_query(text, self.engine)
            cap = self.query_limit if limit is None else int(limit)
            if cap > 0 and len(frame) > cap:
                return frame.head(cap), f"Returned first {cap:,} rows (query limit)."
            return frame, None
        except Exception as exc:
            return None, str(exc)

    def get_tables(self):
        if self.engine is None:
            return []
        try:
            return inspect(self.engine).get_table_names()
        except Exception:
            return []

    def close(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
            self.engine = None
