"""Orquestador paper multi-activo, apto para campañas de semanas o meses."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Iterable

@dataclass(frozen=True)
class PaperCycleResult:
    symbol:str; action:str; details:dict

class MultiAssetPaperRunner:
    def __init__(self, engine, analyzer:Callable[[str],tuple[float,dict]], max_open_positions:int=5, min_confidence:float=72):
        self.engine=engine; self.analyzer=analyzer; self.max_open_positions=max(1,int(max_open_positions)); self.min_confidence=float(min_confidence)
    def cycle(self, symbols:Iterable[str]):
        results=[]
        positions=[p for p in self.engine.storage.get_paper_positions(1000) if p['status']=='OPEN']
        open_count=len(positions)
        for symbol in symbols:
            try:
                price, decision=self.analyzer(symbol)
                marked=self.engine.mark(symbol,price)
                if marked and marked.get('status')=='CLOSED':
                    results.append(PaperCycleResult(symbol,'CLOSED',marked)); open_count=max(0,open_count-1); continue
                if marked:
                    results.append(PaperCycleResult(symbol,'MARKED',marked)); continue
                if open_count>=self.max_open_positions:
                    results.append(PaperCycleResult(symbol,'SKIPPED_LIMIT',{})); continue
                if decision.get('signal') in ('BUY','SELL') and float(decision.get('confidence',0))>=self.min_confidence:
                    pid=self.engine.open_from_decision(symbol,price,decision); open_count+=1
                    results.append(PaperCycleResult(symbol,'OPENED',{'position_id':pid,'price':price,'decision':decision}))
                else: results.append(PaperCycleResult(symbol,'HOLD',{'price':price,'decision':decision}))
            except Exception as exc:
                results.append(PaperCycleResult(symbol,'ERROR',{'error':f'{type(exc).__name__}: {exc}'}))
        return results
