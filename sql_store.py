# sqlite_store.py
import os
import sqlite3
import threading
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.getenv("SQLITE_DB_PATH", "/tmp/estimate_jobs.db")

_init_lock = threading.Lock()
_initialized = False


@contextmanager
def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_table():
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        with _get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_results (
                    job_id      TEXT PRIMARY KEY,
                    status      TEXT NOT NULL,
                    drive_link  TEXT,
                    error       TEXT,
                    updated_at  TEXT NOT NULL
                )
            """)
        _initialized = True


def write_job_result(
    job_id: str,
    status: str,
    drive_link: str = None,
    error: str = None,
) -> None:
    _ensure_table()
    now = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO job_results (job_id, status, drive_link, error, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                status     = excluded.status,
                drive_link = excluded.drive_link,
                error      = excluded.error,
                updated_at = excluded.updated_at
        """, (job_id, status, drive_link, error, now))


def get_job_result(job_id: str) -> dict | None:
    _ensure_table()
    with _get_conn() as conn:
        row = conn.execute("""
            SELECT job_id, status, drive_link, error
            FROM job_results
            WHERE job_id = ?
        """, (job_id,)).fetchone()

    if row is None:
        return None
    return {
        "job_id":     row["job_id"],
        "status":     row["status"],
        "drive_link": row["drive_link"],
        "error":      row["error"],
    }