"""Escáner concurrente multi-activo con límite de concurrencia."""
from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass
from typing import List, TYPE_CHECKING, Any
if TYPE_CHECKING:
    from analyzer_service import MarketAnalyzerService
else:
    MarketAnalyzerService = Any

logger=logging.getLogger(__name__)

DEFAULT_SYMBOLS=('BTC/USDT','ETH/USDT','BNB/USDT','SOL/USDT','XRP/USDT')

@dataclass(frozen=True)
class ScanRow:
    symbol:str; signal:str; confidence:float; score:float; price:float; regime:str; volume_ratio:float

class MarketScanner:
    def __init__(self, service: MarketAnalyzerService, concurrency: int=3): self.service=service; self.semaphore=asyncio.Semaphore(max(1,concurrency))
    async def scan(self, symbols=DEFAULT_SYMBOLS, timeframe='1h', limit=300) -> List[ScanRow]:
        async def one(symbol):
            async with self.semaphore:
                try:
                    r=await self.service.analyze(symbol,timeframe,limit)
                    d=r.decision
                    return ScanRow(symbol,d['signal'],float(d['confidence']),float(d['score']),r.price,
                                   d.get('market_regime',{}).get('regime','—'),float(d.get('volume_ratio',0)))
                except Exception as exc:
                    logger.warning('No se pudo analizar %s: %s', symbol, exc)
                    return ScanRow(symbol,'ERROR',0,0,0,'—',0)
        rows=await asyncio.gather(*(one(s) for s in symbols))
        rank={'BUY':0,'SELL':0,'HOLD':1,'ERROR':2}
        return sorted(rows,key=lambda x:(rank.get(x.signal,3),-x.confidence,-abs(x.score)))
