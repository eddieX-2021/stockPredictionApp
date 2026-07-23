from __future__ import annotations

import json
import os
import sqlite3
import time
from copy import deepcopy
from typing import Any, Callable

from app.services.json_safe import json_safe

CACHE_VERSION = "analysis-v4-phase1-consistency"
DEFAULT_TTL_SECONDS = 6 * 60 * 60
_CACHE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "cache")
)
_DB_PATH = os.path.join(_CACHE_DIR, "analysis_cache.sqlite")


def _connect() -> sqlite3.Connection:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_cache (
            ticker TEXT NOT NULL,
            cache_version TEXT NOT NULL,
            generated_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            payload TEXT NOT NULL,
            PRIMARY KEY (ticker, cache_version)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_analysis_cache_expires ON analysis_cache(expires_at)")
    return conn


def _with_cache_meta(payload: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    next_payload = deepcopy(payload)
    data_quality = next_payload.setdefault("data_quality", {})
    data_quality.setdefault("sources", [])
    data_quality.setdefault("warnings", [])
    data_quality["cache"] = meta
    return next_payload


def get_cached_analysis(ticker: str) -> dict[str, Any] | None:
    now = int(time.time())
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT payload, generated_at, expires_at
            FROM analysis_cache
            WHERE ticker = ? AND cache_version = ?
            """,
            (ticker.upper(), CACHE_VERSION),
        ).fetchone()

    if row is None or int(row["expires_at"]) <= now:
        return None

    payload = json.loads(row["payload"])
    return _with_cache_meta(
        payload,
        {
            "status": "hit",
            "ttl_seconds": max(0, int(row["expires_at"]) - now),
            "generated_at_unix": int(row["generated_at"]),
            "expires_at_unix": int(row["expires_at"]),
            "storage": "sqlite",
            "version": CACHE_VERSION,
        },
    )


def save_analysis(ticker: str, payload: dict[str, Any], ttl_seconds: int = DEFAULT_TTL_SECONDS) -> dict[str, Any]:
    now = int(time.time())
    expires_at = now + ttl_seconds
    safe_payload = json_safe(payload)

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO analysis_cache (ticker, cache_version, generated_at, expires_at, payload)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(ticker, cache_version) DO UPDATE SET
                generated_at = excluded.generated_at,
                expires_at = excluded.expires_at,
                payload = excluded.payload
            """,
            (ticker.upper(), CACHE_VERSION, now, expires_at, json.dumps(safe_payload)),
        )

    return _with_cache_meta(
        safe_payload,
        {
            "status": "miss_saved",
            "ttl_seconds": ttl_seconds,
            "generated_at_unix": now,
            "expires_at_unix": expires_at,
            "storage": "sqlite",
            "version": CACHE_VERSION,
        },
    )


def get_or_build_analysis(
    ticker: str,
    build_fn: Callable[[str], dict[str, Any]],
    *,
    force_refresh: bool = False,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> dict[str, Any]:
    normalized = ticker.upper().strip()
    if not force_refresh:
        cached = get_cached_analysis(normalized)
        if cached is not None:
            return cached

    built = build_fn(normalized)
    return save_analysis(normalized, built, ttl_seconds=ttl_seconds)


def clear_analysis_cache(ticker: str | None = None) -> int:
    with _connect() as conn:
        if ticker:
            cur = conn.execute(
                "DELETE FROM analysis_cache WHERE ticker = ? AND cache_version = ?",
                (ticker.upper(), CACHE_VERSION),
            )
        else:
            cur = conn.execute("DELETE FROM analysis_cache WHERE cache_version = ?", (CACHE_VERSION,))
        return int(cur.rowcount or 0)


def clear_expired_analysis_cache() -> int:
    now = int(time.time())
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM analysis_cache WHERE expires_at <= ? OR cache_version != ?",
            (now, CACHE_VERSION),
        )
        return int(cur.rowcount or 0)


def get_analysis_cache_stats() -> dict[str, Any]:
    now = int(time.time())
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT ticker, generated_at, expires_at, LENGTH(payload) AS bytes
            FROM analysis_cache
            WHERE cache_version = ?
            ORDER BY ticker
            """,
            (CACHE_VERSION,),
        ).fetchall()

    entries = []
    active = 0
    expired = 0
    total_bytes = 0
    for row in rows:
        is_expired = int(row["expires_at"]) <= now
        active += 0 if is_expired else 1
        expired += 1 if is_expired else 0
        total_bytes += int(row["bytes"] or 0)
        entries.append(
            {
                "ticker": row["ticker"],
                "generated_at_unix": int(row["generated_at"]),
                "expires_at_unix": int(row["expires_at"]),
                "ttl_seconds": max(0, int(row["expires_at"]) - now),
                "expired": is_expired,
                "bytes": int(row["bytes"] or 0),
            }
        )

    return {
        "db_path": _DB_PATH,
        "version": CACHE_VERSION,
        "default_ttl_seconds": DEFAULT_TTL_SECONDS,
        "total_entries": len(entries),
        "active_entries": active,
        "expired_entries": expired,
        "approx_payload_bytes": total_bytes,
        "entries": entries,
    }
