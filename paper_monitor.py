"""Seguimiento prolongado de paper trading con snapshots diarios."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime,timezone
import json
from pathlib import Path

@dataclass
class PaperSnapshot:
    timestamp:str; balance:float; realized_pnl:float; open_positions:int

class PaperTradingJournal:
    def __init__(self,path:str): self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
    def append(self,account:dict,open_positions:int)->PaperSnapshot:
        snap=PaperSnapshot(datetime.now(timezone.utc).isoformat(),float(account['balance']),float(account['realized_pnl']),int(open_positions))
        with self.path.open('a',encoding='utf-8') as f:f.write(json.dumps(snap.__dict__,ensure_ascii=False)+'\n')
        return snap
    def read(self,limit:int=365):
        if not self.path.exists():return []
        lines=self.path.read_text(encoding='utf-8').splitlines()[-limit:]; return [json.loads(x) for x in lines if x.strip()]
