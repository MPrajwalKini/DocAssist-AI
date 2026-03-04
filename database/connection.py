"""
SQLite connection manager with WAL mode for concurrent reads.
Provides get_db() context manager and init_db() for schema creation.
"""
import sqlite3
import os
from contextlib import contextmanager
from config import DATABASE_PATH
from database.models import SCHEMA_SQL


def _ensure_db_dir():
    """Create the directory for the database file if it doesn't exist."""
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Create a new SQLite connection with WAL mode and foreign keys enabled."""
    _ensure_db_dir()
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    """
    Context manager for database connections.

    Usage:
        with get_db() as db:
            db.execute("SELECT ...")
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database schema. Safe to call multiple times."""
    with get_db() as db:
        db.executescript(SCHEMA_SQL)


# ── Convenience query helpers ─────────────────────────────────────────────────

def fetch_one(query: str, params: tuple = ()) -> dict | None:
    """Execute a query and return one row as a dict, or None."""
    with get_db() as db:
        row = db.execute(query, params).fetchone()
        return dict(row) if row else None


def fetch_all(query: str, params: tuple = ()) -> list[dict]:
    """Execute a query and return all rows as a list of dicts."""
    with get_db() as db:
        rows = db.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def execute(query: str, params: tuple = ()) -> int:
    """Execute a write query and return lastrowid."""
    with get_db() as db:
        cursor = db.execute(query, params)
        return cursor.lastrowid
