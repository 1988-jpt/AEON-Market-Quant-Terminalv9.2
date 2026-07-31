"""Monitor público de liquidaciones USD-M de Binance."""
from __future__ import annotations
import asyncio,json,logging
from dataclasses import dataclass
from typing import Awaitable,Callable,Optional
logger=logging.getLogger(__name__)

@dataclass(frozen=True)
class LiquidationEvent:
    symbol:str; side:str; price:float; quantity:float; average_price:float; status:str; timestamp_ms:int

def parse_liquidation(payload:dict)->LiquidationEvent:
    order=payload.get('o',payload)
    return LiquidationEvent(str(order['s']),str(order['S']),float(order['p']),float(order['q']),float(order.get('ap') or 0),str(order.get('X','')),int(order.get('T') or payload.get('E') or 0))

class LiquidationStream:
    URL='wss://fstream.binance.com/ws/!forceOrder@arr'
    def __init__(self,on_event:Callable[[LiquidationEvent],Awaitable[None]],on_status:Optional[Callable[[str],Awaitable[None]]]=None):
        self.on_event=on_event; self.on_status=on_status; self.stop_event=asyncio.Event(); self.socket=None
    async def stop(self):
        self.stop_event.set()
        if self.socket:
            try: await self.socket.close()
            except Exception: pass
    async def run(self):
        import websockets
        delay=1
        while not self.stop_event.is_set():
            try:
                if self.on_status: await self.on_status('Conectando liquidaciones')
                async with websockets.connect(self.URL,ping_interval=20,ping_timeout=20,max_queue=256) as ws:
                    self.socket=ws; delay=1
                    if self.on_status: await self.on_status('Liquidaciones conectadas')
                    while not self.stop_event.is_set():
                        raw=await asyncio.wait_for(ws.recv(),35); payload=json.loads(raw)
                        events=payload if isinstance(payload,list) else [payload]
                        for item in events:
                            try: await self.on_event(parse_liquidation(item))
                            except (KeyError,TypeError,ValueError): logger.warning('Liquidación inválida descartada',exc_info=True)
            except asyncio.CancelledError: break
            except Exception as exc:
                if self.stop_event.is_set(): break
                logger.warning('Stream liquidaciones interrumpido: %s',exc)
                await asyncio.sleep(delay); delay=min(delay*2,30)
        self.socket=None
