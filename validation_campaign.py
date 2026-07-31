"""Campañas reproducibles de 30-90 días y comparación backtest/paper/testnet."""
from __future__ import annotations
import json, sqlite3
from datetime import datetime, timezone
from pathlib import Path

class CampaignStore:
    def __init__(self,path='data/validation_campaigns.db'):
        self.path=str(path); Path(self.path).parent.mkdir(parents=True,exist_ok=True); self._init()
    def _conn(self): c=sqlite3.connect(self.path); c.row_factory=sqlite3.Row; return c
    def _init(self):
        with self._conn() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS observations(id INTEGER PRIMARY KEY AUTOINCREMENT,ts TEXT NOT NULL,source TEXT NOT NULL,symbol TEXT NOT NULL,signal TEXT,price REAL,pnl REAL,latency_ms REAL,ok INTEGER NOT NULL,error TEXT,details TEXT)''')
            c.execute('CREATE INDEX IF NOT EXISTS ix_obs_source_symbol_ts ON observations(source,symbol,ts)')
    def record(self,source,symbol,signal=None,price=None,pnl=None,latency_ms=None,ok=True,error=None,details=None):
        with self._conn() as c:
            c.execute('INSERT INTO observations(ts,source,symbol,signal,price,pnl,latency_ms,ok,error,details) VALUES(?,?,?,?,?,?,?,?,?,?)',
             (datetime.now(timezone.utc).isoformat(),source,symbol,signal,price,pnl,latency_ms,int(ok),error,json.dumps(details or {},default=str)))
    def compare(self,symbol):
        with self._conn() as c:
            rows=c.execute('SELECT * FROM observations WHERE symbol=? ORDER BY id',(symbol,)).fetchall()
        groups={}
        for r in rows: groups.setdefault(r['source'],[]).append(dict(r))
        summary={}
        for source,items in groups.items():
            ok=sum(x['ok'] for x in items); pnls=[x['pnl'] for x in items if x['pnl'] is not None]; signals=[x['signal'] for x in items if x['signal']]
            summary[source]={'samples':len(items),'availability_pct':round(ok/len(items)*100,2) if items else 0,'total_pnl':round(sum(pnls),8),'signals':len(signals)}
        sources=list(summary); agreement=None
        if len(sources)>=2:
            sequences={s:[x['signal'] for x in groups[s] if x['signal']] for s in sources}
            base=sequences[sources[0]]; comparisons=[]
            for s in sources[1:]:
                n=min(len(base),len(sequences[s]));
                if n: comparisons.append(sum(a==b for a,b in zip(base[-n:],sequences[s][-n:]))/n)
            agreement=round(sum(comparisons)/len(comparisons)*100,2) if comparisons else None
        return {'symbol':symbol,'sources':summary,'signal_agreement_pct':agreement}
