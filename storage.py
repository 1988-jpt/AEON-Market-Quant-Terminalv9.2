"""Persistencia SQLite con migraciones seguras para señales y backtesting."""
from __future__ import annotations
import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Dict, List, Optional
from config import DB_PATH

logger = logging.getLogger(__name__)

class Storage:
    _lock = threading.RLock()
    SCHEMA_VERSION = 4

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or DB_PATH)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=15, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA busy_timeout=15000')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA temp_store=MEMORY')
        return conn

    @staticmethod
    def _unique_indexes(conn: sqlite3.Connection, table: str) -> list[tuple[str, ...]]:
        result: list[tuple[str, ...]] = []
        for row in conn.execute(f"PRAGMA index_list('{table}')").fetchall():
            # PRAGMA index_list: seq, name, unique, origin, partial
            if not int(row[2]):
                continue
            name = row[1]
            columns = tuple(
                item[2] for item in conn.execute(f"PRAGMA index_info('{name}')").fetchall()
            )
            result.append(columns)
        return result

    def _migrate_signals(self, conn: sqlite3.Connection) -> None:
        """Convierte esquemas antiguos sin perder el historial.

        V1 usaba UNIQUE(ts, symbol, signal). V2 usa UNIQUE(ts, symbol), porque
        una vela debe tener un único estado final. SQLite no permite cambiar
        una restricción UNIQUE directamente, así que reconstruimos la tabla.
        """
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='signals'"
        ).fetchone()
        if not exists:
            conn.execute(
                "CREATE TABLE signals("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "ts INTEGER NOT NULL,symbol TEXT NOT NULL,signal TEXT NOT NULL,"
                "price REAL NOT NULL,details TEXT,UNIQUE(ts,symbol))"
            )
            return

        unique_indexes = self._unique_indexes(conn, 'signals')
        if ('ts', 'symbol') in unique_indexes:
            return

        logger.info('Migrando tabla signals al esquema V2...')
        conn.execute('ALTER TABLE signals RENAME TO signals_legacy')
        conn.execute(
            "CREATE TABLE signals("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "ts INTEGER NOT NULL,symbol TEXT NOT NULL,signal TEXT NOT NULL,"
            "price REAL NOT NULL,details TEXT,UNIQUE(ts,symbol))"
        )
        # Conserva la fila más reciente de cada combinación timestamp/símbolo.
        conn.execute(
            "INSERT INTO signals(ts,symbol,signal,price,details) "
            "SELECT s.ts,s.symbol,s.signal,s.price,s.details "
            "FROM signals_legacy s "
            "JOIN (SELECT ts,symbol,MAX(id) AS max_id FROM signals_legacy "
            "GROUP BY ts,symbol) latest ON latest.max_id=s.id"
        )
        conn.execute('DROP TABLE signals_legacy')
        logger.info('Migración de signals completada.')

    def _init_db(self):
        with self._lock, self._conn() as conn:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA foreign_keys=ON')
            self._migrate_signals(conn)
            conn.execute('CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT)')
            conn.execute(
                'CREATE TABLE IF NOT EXISTS backtest_runs('
                'id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,'
                'symbol TEXT NOT NULL,timeframe TEXT NOT NULL,period_start TEXT,'
                'period_end TEXT,config_json TEXT NOT NULL,metrics_json TEXT NOT NULL,'
                'report_dir TEXT)'
            )
            conn.execute(
                'CREATE TABLE IF NOT EXISTS backtest_trades('
                'id INTEGER PRIMARY KEY AUTOINCREMENT,run_id INTEGER NOT NULL,'
                'trade_no INTEGER NOT NULL,trade_json TEXT NOT NULL,'
                'FOREIGN KEY(run_id) REFERENCES backtest_runs(id) ON DELETE CASCADE)'
            )
            conn.execute(
                'CREATE TABLE IF NOT EXISTS paper_accounts('
                'id INTEGER PRIMARY KEY CHECK(id=1),balance REAL NOT NULL,'
                'initial_balance REAL NOT NULL,realized_pnl REAL NOT NULL DEFAULT 0,'
                'updated_at TEXT NOT NULL)'
            )
            conn.execute(
                'CREATE TABLE IF NOT EXISTS paper_positions('
                'id INTEGER PRIMARY KEY AUTOINCREMENT,symbol TEXT NOT NULL,side TEXT NOT NULL,'
                'entry REAL NOT NULL,quantity REAL NOT NULL,stop REAL NOT NULL,target REAL NOT NULL,'
                'opened_at TEXT NOT NULL,closed_at TEXT,exit REAL,gross_pnl REAL,fees REAL,net_pnl REAL,'
                "confidence REAL NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'OPEN',exit_reason TEXT)"
            )
            conn.execute(
                'CREATE UNIQUE INDEX IF NOT EXISTS ux_paper_open_symbol '
                "ON paper_positions(symbol) WHERE status='OPEN'"
            )
            conn.execute(
                "INSERT INTO metadata(key,value) VALUES('schema_version',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(self.SCHEMA_VERSION),),
            )
            conn.commit()

    def insert_signal(self, ts, symbol, signal, price, details=None):
        with self._lock, self._conn() as conn:
            cur = conn.execute(
                'INSERT INTO signals(ts,symbol,signal,price,details) VALUES(?,?,?,?,?) '
                'ON CONFLICT(ts,symbol) DO UPDATE SET '
                'signal=excluded.signal,price=excluded.price,details=excluded.details',
                (ts, symbol, signal, price, details),
            )
            conn.commit()
            return cur.rowcount > 0

    def get_recent_signals(self, limit=30) -> List[Dict]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                'SELECT id,ts,symbol,signal,price,details FROM signals '
                'ORDER BY ts DESC LIMIT ?',
                (max(1, min(int(limit), 500)),),
            ).fetchall()
            return [dict(row) for row in rows]

    def save_backtest(self, symbol, timeframe, period_start, period_end, result, report_dir=''):
        from datetime import datetime, timezone
        with self._lock, self._conn() as conn:
            cur = conn.execute(
                'INSERT INTO backtest_runs(created_at,symbol,timeframe,period_start,'
                'period_end,config_json,metrics_json,report_dir) VALUES(?,?,?,?,?,?,?,?)',
                (datetime.now(timezone.utc).isoformat(), symbol, timeframe,
                 period_start, period_end, json.dumps(result.config, default=str),
                 json.dumps(result.metrics, default=str), report_dir),
            )
            run_id = cur.lastrowid
            conn.executemany(
                'INSERT INTO backtest_trades(run_id,trade_no,trade_json) VALUES(?,?,?)',
                [(run_id, i + 1, json.dumps(t, default=str))
                 for i, t in enumerate(result.trades)],
            )
            conn.commit()
            return run_id

    def set_metadata(self, key, value):
        with self._lock, self._conn() as conn:
            conn.execute(
                'INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)',
                (key, value),
            )
            conn.commit()

    def get_metadata(self, key):
        with self._lock, self._conn() as conn:
            row = conn.execute('SELECT value FROM metadata WHERE key=?', (key,)).fetchone()
            return row['value'] if row else None



    def get_paper_statistics(self) -> Dict:
        """Resumen verificable de operaciones paper cerradas."""
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total, "
                "SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) AS wins, "
                "COALESCE(SUM(net_pnl), 0) AS net_pnl "
                "FROM paper_positions WHERE status='CLOSED'"
            ).fetchone()
            total = int(row['total'] or 0)
            wins = int(row['wins'] or 0)
            return {
                'total': total,
                'wins': wins,
                'win_rate_pct': round((wins / total * 100.0), 1) if total else None,
                'net_pnl': float(row['net_pnl'] or 0.0),
            }

    def ensure_paper_account(self, initial_balance=10000.0):
        from datetime import datetime, timezone
        with self._lock, self._conn() as conn:
            conn.execute(
                'INSERT OR IGNORE INTO paper_accounts(id,balance,initial_balance,realized_pnl,updated_at) '
                'VALUES(1,?,?,0,?)',
                (float(initial_balance), float(initial_balance), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()

    def get_paper_account(self):
        self.ensure_paper_account()
        with self._lock, self._conn() as conn:
            row = conn.execute('SELECT * FROM paper_accounts WHERE id=1').fetchone()
            return dict(row)

    def open_paper_position(self, position):
        with self._lock, self._conn() as conn:
            cur = conn.execute(
                'INSERT INTO paper_positions(symbol,side,entry,quantity,stop,target,opened_at,confidence) '
                'VALUES(?,?,?,?,?,?,?,?)',
                (position['symbol'], position['side'], position['entry'], position['quantity'],
                 position['stop'], position['target'], position['opened_at'], position['confidence']),
            )
            conn.commit()
            return int(cur.lastrowid)

    def get_open_paper_position(self, symbol):
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM paper_positions WHERE symbol=? AND status='OPEN' ORDER BY id DESC LIMIT 1",
                (symbol.strip().upper(),),
            ).fetchone()
            return dict(row) if row else None

    def close_paper_position(self, position_id, exit_price, gross, fees, net, reason):
        from datetime import datetime, timezone
        with self._lock, self._conn() as conn:
            row = conn.execute("SELECT * FROM paper_positions WHERE id=? AND status='OPEN'",
                               (int(position_id),)).fetchone()
            if not row:
                raise ValueError('La posición paper ya está cerrada o no existe.')
            closed_at = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "UPDATE paper_positions SET status='CLOSED',closed_at=?,exit=?,gross_pnl=?,fees=?,net_pnl=?,exit_reason=? WHERE id=?",
                (closed_at, float(exit_price), float(gross), float(fees), float(net), str(reason), int(position_id)),
            )
            conn.execute(
                'UPDATE paper_accounts SET balance=balance+?,realized_pnl=realized_pnl+?,updated_at=? WHERE id=1',
                (float(net), float(net), closed_at),
            )
            conn.commit()
            result = dict(row)
            result.update({'status':'CLOSED','closed_at':closed_at,'exit':float(exit_price),
                           'gross_pnl':float(gross),'fees':float(fees),'net_pnl':float(net),
                           'exit_reason':str(reason)})
            return result

    def get_paper_positions(self, limit=100):
        with self._lock, self._conn() as conn:
            rows = conn.execute('SELECT * FROM paper_positions ORDER BY id DESC LIMIT ?',
                                (max(1, min(int(limit), 1000)),)).fetchall()
            return [dict(row) for row in rows]
