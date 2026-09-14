from __future__ import annotations
import json, sqlite3, os
from datetime import datetime, timezone
from app.config import settings


def _connect():
    os.makedirs(os.path.dirname(settings.db_path) or '.', exist_ok=True)
    con = sqlite3.connect(settings.db_path)
    con.execute('CREATE TABLE IF NOT EXISTS scans (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)')
    con.execute('CREATE TABLE IF NOT EXISTS paper_trades (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, symbol TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, exit_price REAL, exit_reason TEXT, pnl_usd REAL, closed_at TEXT)')
    con.execute('CREATE TABLE IF NOT EXISTS paper_trade_events (id INTEGER PRIMARY KEY, trade_id INTEGER NOT NULL, created_at TEXT NOT NULL, quantity REAL NOT NULL, exit_price REAL NOT NULL, reason TEXT NOT NULL, pnl_usd REAL NOT NULL)')
    for col, typ in [('exit_price', 'REAL'), ('exit_reason', 'TEXT'), ('pnl_usd', 'REAL'), ('closed_at', 'TEXT')]:
        try:
            con.execute(f'ALTER TABLE paper_trades ADD COLUMN {col} {typ}')
        except sqlite3.OperationalError:
            pass
    # Migrate legacy fully-closed trades into the event ledger exactly once.
    # Partial legacy fills cannot be reconstructed, so only trades with no event
    # and a complete closed-trade PnL are backfilled.
    con.execute(
        'INSERT INTO paper_trade_events(trade_id,created_at,quantity,exit_price,reason,pnl_usd) '
        'SELECT p.id, COALESCE(p.closed_at,p.created_at), '
        'CAST(json_extract(p.payload, "$.position_size") AS REAL), '
        'COALESCE(p.exit_price, CAST(json_extract(p.payload, "$.entry") AS REAL)), '
        'COALESCE(p.exit_reason, "LEGACY_CLOSE"), COALESCE(p.pnl_usd, 0) '
        'FROM paper_trades p '
        'WHERE p.status="CLOSED" AND COALESCE(p.pnl_usd,0) != 0 '
        'AND NOT EXISTS (SELECT 1 FROM paper_trade_events e WHERE e.trade_id=p.id)'
    )
    con.commit()
    return con


def save_scan(results):
    with _connect() as con:
        con.execute('INSERT INTO scans(created_at,payload) VALUES (?,?)', (datetime.now(timezone.utc).isoformat(), json.dumps([x.model_dump(mode='json') for x in results])))
        con.commit()


def create_paper_trade(plan):
    payload = plan.model_dump(mode='json')
    payload['remaining_size'] = float(plan.position_size)
    payload['tp1_hit'] = False
    payload['tp2_hit'] = False
    payload['breakeven_armed'] = False
    with _connect() as con:
        cur = con.execute('INSERT INTO paper_trades(created_at,symbol,payload,status) VALUES (?,?,?,?)', (datetime.now(timezone.utc).isoformat(), plan.symbol, json.dumps(payload), 'OPEN'))
        con.commit()
        return cur.lastrowid


def list_paper_trades(limit=100):
    with _connect() as con:
        rows = con.execute('SELECT id,created_at,symbol,payload,status,exit_price,exit_reason,pnl_usd,closed_at FROM paper_trades ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
    return [{'id': r[0], 'created_at': r[1], 'symbol': r[2], 'payload': json.loads(r[3]), 'status': r[4], 'exit_price': r[5], 'exit_reason': r[6], 'pnl_usd': r[7], 'closed_at': r[8]} for r in rows]


def open_paper_trades():
    with _connect() as con:
        rows = con.execute('SELECT id,symbol,payload FROM paper_trades WHERE status="OPEN" ORDER BY id').fetchall()
    return [{'id': r[0], 'symbol': r[1], 'payload': json.loads(r[2])} for r in rows]


def realized_pnl_since(start: datetime) -> float:
    start_iso = start.astimezone(timezone.utc).isoformat()
    with _connect() as con:
        row = con.execute('SELECT COALESCE(SUM(pnl_usd), 0) FROM paper_trade_events WHERE created_at >= ?', (start_iso,)).fetchone()
    return float(row[0] or 0.0)


def update_paper_trade_payload(trade_id, payload):
    with _connect() as con:
        con.execute('UPDATE paper_trades SET payload=? WHERE id=? AND status="OPEN"', (json.dumps(payload), trade_id))
        con.commit()


def close_paper_trade(trade_id, exit_price, reason, quantity=None):
    with _connect() as con:
        row = con.execute('SELECT symbol,payload,pnl_usd FROM paper_trades WHERE id=? AND status="OPEN"', (trade_id,)).fetchone()
        if not row:
            return None
        plan = json.loads(row[1])
        remaining = float(plan.get('remaining_size', plan['position_size']))
        qty = min(remaining, float(quantity)) if quantity is not None else remaining
        if qty <= 0:
            return 0.0
        exit_price = float(exit_price)
        pnl = (exit_price - float(plan['entry'])) * qty
        left = remaining - qty
        accumulated = float(row[2] or 0.0) + pnl
        now = datetime.now(timezone.utc).isoformat()
        con.execute('INSERT INTO paper_trade_events(trade_id,created_at,quantity,exit_price,reason,pnl_usd) VALUES (?,?,?,?,?,?)', (trade_id, now, qty, exit_price, reason, pnl))
        if left <= 1e-12:
            con.execute('UPDATE paper_trades SET status="CLOSED",exit_price=?,exit_reason=?,pnl_usd=?,closed_at=? WHERE id=?', (exit_price, reason, accumulated, now, trade_id))
        else:
            plan['remaining_size'] = left
            con.execute('UPDATE paper_trades SET payload=?,pnl_usd=?,exit_reason=? WHERE id=? AND status="OPEN"', (json.dumps(plan), accumulated, reason, trade_id))
        con.commit()
        return pnl
