from __future__ import annotations
import json, sqlite3, os
from datetime import datetime, timezone
from app.config import settings


def _connect():
    os.makedirs(os.path.dirname(settings.db_path) or '.', exist_ok=True)
    con=sqlite3.connect(settings.db_path)
    con.execute('CREATE TABLE IF NOT EXISTS scans (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)')
    con.execute('CREATE TABLE IF NOT EXISTS paper_trades (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, symbol TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL)')
    con.commit(); return con


def save_scan(results):
    with _connect() as con:
        con.execute('INSERT INTO scans(created_at,payload) VALUES (?,?)',(datetime.now(timezone.utc).isoformat(),json.dumps([x.model_dump(mode="json") for x in results])))
        con.commit()


def create_paper_trade(plan):
    with _connect() as con:
        cur=con.execute('INSERT INTO paper_trades(created_at,symbol,payload,status) VALUES (?,?,?,?)',(datetime.now(timezone.utc).isoformat(),plan.symbol,json.dumps(plan.model_dump(mode="json")),'OPEN'))
        con.commit(); return cur.lastrowid


def list_paper_trades(limit=100):
    with _connect() as con:
        rows=con.execute('SELECT id,created_at,symbol,payload,status FROM paper_trades ORDER BY id DESC LIMIT ?',(limit,)).fetchall()
    return [{'id':r[0],'created_at':r[1],'symbol':r[2],'payload':json.loads(r[3]),'status':r[4]} for r in rows]
