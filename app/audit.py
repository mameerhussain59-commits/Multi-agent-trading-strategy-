from __future__ import annotations

import json
from datetime import datetime, timezone

from app.storage import _connect


def record_event(event_type: str, symbol: str | None, payload: dict) -> None:
    """Persist an auditable decision/event without inventing market observations."""
    with _connect() as con:
        con.execute(
            'CREATE TABLE IF NOT EXISTS audit_events ('
            'id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, event_type TEXT NOT NULL, '
            'symbol TEXT, payload TEXT NOT NULL)'
        )
        con.execute(
            'INSERT INTO audit_events(created_at,event_type,symbol,payload) VALUES (?,?,?,?)',
            (datetime.now(timezone.utc).isoformat(), event_type, symbol, json.dumps(payload)),
        )
        con.commit()


def list_events(limit: int = 200):
    with _connect() as con:
        con.execute(
            'CREATE TABLE IF NOT EXISTS audit_events ('
            'id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, event_type TEXT NOT NULL, '
            'symbol TEXT, payload TEXT NOT NULL)'
        )
        rows = con.execute(
            'SELECT id,created_at,event_type,symbol,payload FROM audit_events '
            'ORDER BY id DESC LIMIT ?', (limit,)
        ).fetchall()
    return [
        {'id': r[0], 'created_at': r[1], 'event_type': r[2], 'symbol': r[3], 'payload': json.loads(r[4])}
        for r in rows
    ]
