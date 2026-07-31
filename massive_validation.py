"""Validación masiva multi-activo con agregación robusta."""
from __future__ import annotations
import asyncio,statistics

class MassiveValidator:
    def __init__(self,backtest_service,concurrency:int=2): self.service=backtest_service; self.limit=asyncio.Semaphore(max(1,concurrency))
    async def run(self,symbols,timeframes=('1h','4h'),bars=5000,config=None):
        async def one(s,t):
            async with self.limit:
                try:
                    r=await self.service.run(s,t,bars,False,config,None,None,True); m=r.result.metrics
                    return {'symbol':s,'timeframe':t,'ok':True,'return_pct':float(m['net_return_pct']),'profit_factor':float(m['profit_factor'] if m['profit_factor']!='inf' else 99),'drawdown_pct':float(m['max_drawdown_pct']),'trades':int(m['total_trades'])}
                except Exception as e:return {'symbol':s,'timeframe':t,'ok':False,'error':str(e)}
        rows=await asyncio.gather(*(one(s,t) for s in symbols for t in timeframes)); good=[r for r in rows if r['ok']]
        return {'rows':rows,'successful':len(good),'failed':len(rows)-len(good),'positive_pct':100*sum(r['return_pct']>0 for r in good)/len(good) if good else 0,'median_return_pct':statistics.median([r['return_pct'] for r in good]) if good else 0,'median_profit_factor':statistics.median([r['profit_factor'] for r in good]) if good else 0}
