"""Servicio de análisis Android sin Pandas."""
from __future__ import annotations
from typing import Optional
from binance_client import BinanceClient
from config import OHLCV_LIMIT,OHLCV_TIMEFRAME
from mobile_market_core import analyze_ohlcv
from storage import Storage

class AndroidMarketAnalyzerService:
    def __init__(self,db_path:Optional[str]=None,client:Optional[BinanceClient]=None):
        self.storage=Storage(db_path); self.client=client or BinanceClient()
    async def analyze(self,symbol:str,timeframe:str=OHLCV_TIMEFRAME,limit:int=OHLCV_LIMIT,**_):
        rows=await self.client.fetch_ohlcv(symbol,timeframe=timeframe,limit=limit)
        result=analyze_ohlcv(rows,symbol.strip().upper(),timeframe)
        d=result.decision; saved=self.storage.insert_signal(result.timestamp_ms,result.symbol,d['signal'],result.price,f"{d['reason']} | Calidad técnica: {d['confidence']:.1f}")
        return type(result)(result.symbol,result.timeframe,result.price,result.timestamp_ms,d,result.dataframe,result.news,result.sentiment,saved)
    async def close(self): await self.client.close()
