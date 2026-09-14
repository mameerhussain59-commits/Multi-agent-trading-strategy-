from __future__ import annotations
import json, sqlite3, os
from datetime import datetime, timezone
from app.config import settings


def _connect():
    os.makedirs(os.path.dirname(settings.db_path) or '.', exist_ok=True)
    con = sqlite3.connect(settings.db_path)
    con.execute('CREATE TABLE IF NOT EXISTS scans (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)')
    con.execute('CREATE TABLE IF NOT EXISTS paper_trades (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, symbol TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, exit_price REAL, exit_reason TEXT, pnl_usd REAL)')
    for col, typ in [('exit_price', 'REAL'), ('exit_reason', 'TEXT'), ('pnl_usd', 'REAL')]:
        try:
            con.execute(f'ALTER TABLE paper_trades ADD COLUMN {col} {typ}')
        except sqlite3.OperationalError:
            pass
    con.commit()
    return con


def save_scan(results):
    with _connect() as con:
        con.execute(
            'INSERT INTO scans(created_at,payload) VALUES (?,?)',
            (datetime.now(timezone.utc).isoformat(), json.dumps([x.model_dump(mode='json') for x in results])),
        )
        con.commit()


def create_paper_trade(plan):
    with _connect() as con:
        cur = con.execute(
            'INSERT INTO paper_trades(created_at,symbol,payload,status) VALUES (?,?,?,?)',
            (datetime.now(timezone.utc).isoformat(), plan.symbol, json.dumps(plan.model_dump(mode='json')), 'OPEN'),
        )
        con.commit()
        return cur.lastrowid


def list_paper_trades(limit=100):
    with _connect() as con:
        rows = con.execute(
            'SELECT id,created_at,symbol,payload,status,exit_price,exit_reason,pnl_usd '
            'FROM paper_trades ORDER BY id DESC LIMIT ?', (limit,)
        ).fetchall()
    return [
        {'id': r[0], 'created_at': r[1], 'symbol': r[2], 'payload': json.loads(r[3]),
         'status': r[4], 'exit_price': r[5], 'exit_reason': r[6], 'pnl_usd': r[7]}
        for r in rows
    ]


def open_paper_trades():
    with _connect() as con:
        rows = con.execute('SELECT id,symbol,payload FROM paper_trades WHERE status="OPEN" ORDER BY id').fetchall()
    return [{'id': r[0], 'symbol': r[1], 'payload': json.loads(r[2])} for r in rows]


def realized_pnl_since(start: datetime) -> float:
    start_iso = start.astimezone(timezone.utc).isoformat()
    with _connect() as con:
        row = con.execute(
            'SELECT COALESCE(SUM(pnl_usd), 0) FROM paper_trades '
            'WHERE status="CLOSED" AND created_at >= ?', (start_iso,)
        ).fetchone()
    return float(row[0] or 0.0)


def close_paper_trade(trade_id, exit_price, reason):
    with _connect() as con:
        row = con.execute(
            'SELECT payload FROM paper_trades WHERE id=? AND status="OPEN"', (trade_id,)
        ).fetchone()
        if not row:
            return None
        plan = json.loads(row[0])
        qty = float(plan['position_size'])
        pnl = (float(exit_price) - float(plan['entry'])) * qty
        con.execute(
            'UPDATE paper_trades SET status="CLOSED",exit_price=?,exit_reason=?,pnl_usd=? WHERE id=?',
            (exit_price, reason, pnl, trade_id),
        )
        con.commit()
        return pnl
