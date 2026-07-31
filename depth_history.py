"""Persistencia histórica de snapshots de profundidad en SQLite."""
from __future__ import annotations
import json, sqlite3, threading
from datetime import datetime, timezone
from pathlib import Path
from order_book import analyze_order_book

class DepthHistoryStore:
    def __init__(self, path='data/market_microstructure.db'):
        self.path=str(path); Path(self.path).parent.mkdir(parents=True, exist_ok=True); self._lock=threading.RLock(); self._init()
    def _conn(self):
        c=sqlite3.connect(self.path, timeout=15); c.row_factory=sqlite3.Row; return c
    def _init(self):
        with self._lock, self._conn() as c:
            c.execute('PRAGMA journal_mode=WAL')
            c.execute('''CREATE TABLE IF NOT EXISTS depth_snapshots(
                id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, symbol TEXT NOT NULL,
                best_bid REAL NOT NULL,best_ask REAL NOT NULL,spread_bps REAL NOT NULL,
                bid_depth REAL NOT NULL,ask_depth REAL NOT NULL,imbalance REAL NOT NULL,
                raw_json TEXT)''')
            c.execute('CREATE INDEX IF NOT EXISTS ix_depth_symbol_ts ON depth_snapshots(symbol,ts)')
    def record(self,symbol,bids,asks,levels=20):
        m=analyze_order_book(bids,asks,levels); ts=datetime.now(timezone.utc).isoformat()
        raw=json.dumps({'bids':list(bids)[:levels],'asks':list(asks)[:levels]})
        with self._lock,self._conn() as c:
            cur=c.execute('INSERT INTO depth_snapshots(ts,symbol,best_bid,best_ask,spread_bps,bid_depth,ask_depth,imbalance,raw_json) VALUES(?,?,?,?,?,?,?,?,?)',
                (ts,symbol.upper(),m.best_bid,m.best_ask,m.spread_bps,m.bid_depth,m.ask_depth,m.imbalance,raw)); c.commit(); return cur.lastrowid
    def recent(self,symbol,limit=100):
        with self._lock,self._conn() as c:
            rows=c.execute('SELECT * FROM depth_snapshots WHERE symbol=? ORDER BY id DESC LIMIT ?', (symbol.upper(),max(1,min(int(limit),10000)))).fetchall(); return [dict(x) for x in rows]
