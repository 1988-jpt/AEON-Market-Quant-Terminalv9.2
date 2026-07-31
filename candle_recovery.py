"""Recuperación de velas perdidas tras suspensión o cortes de WebSocket."""
from __future__ import annotations
from binance_rest_client import TIMEFRAME_MS

class CandleRecoveryManager:
    def __init__(self,client): self.client=client
    async def recover(self,symbol:str,timeframe:str,last_open_ms:int,current_open_ms:int):
        step=TIMEFRAME_MS[timeframe]
        if current_open_ms-last_open_ms<=step:return []
        missing=max(0,(current_open_ms-last_open_ms)//step-1)
        if not missing:return []
        rows=await self.client.fetch_ohlcv_range(symbol,timeframe,since_ms=last_open_ms+step,until_ms=current_open_ms-step,limit=int(missing)+2)
        unique={int(r[0]):r for r in rows if last_open_ms<int(r[0])<current_open_ms}
        return [unique[k] for k in sorted(unique)]
