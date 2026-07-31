"""Flujo de mercado móvil: WebSocket rápido y respaldo REST con velas OHLCV reales."""
from __future__ import annotations
import asyncio, json, logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional
from config import VALID_TIMEFRAMES
logger=logging.getLogger(__name__)

@dataclass(frozen=True)
class RealtimeTick:
    symbol:str; timeframe:str; timestamp_ms:int; open:float; high:float; low:float; close:float; volume:float; closed:bool
TickCallback=Callable[[RealtimeTick],Awaitable[None]]
StatusCallback=Callable[[str],Awaitable[None]]
GapCallback=Callable[[int,int],Awaitable[None]]

def _stream_symbol(symbol:str)->str:
    value=symbol.strip().lower().replace('/','').replace('-','')
    if not value.isalnum():raise ValueError('Símbolo inválido')
    return value

def _interval_ms(tf:str)->int:
    unit=tf[-1]; n=int(tf[:-1]); return n*{'m':60000,'h':3600000,'d':86400000}[unit]

class BinanceRealtimeFeed:
    WS_BASES=('wss://stream.binance.com:443/ws','wss://data-stream.binance.vision/ws','wss://stream.binance.com:9443/ws')
    REST_BASES=('https://api.binance.com','https://api1.binance.com','https://api2.binance.com','https://api3.binance.com','https://data-api.binance.vision')
    def __init__(self,symbol,timeframe,on_tick,on_status=None,on_gap=None):
        self.symbol=symbol.strip().upper().replace('-','/'); self.timeframe=timeframe
        if timeframe not in VALID_TIMEFRAMES:raise ValueError(f'Temporalidad no compatible: {timeframe}')
        self.on_tick=on_tick; self.on_status=on_status; self.on_gap=on_gap
        self._last_open_ms=None; self._stop_event=asyncio.Event(); self._socket=None
    async def _status(self,text):
        logger.info('Tiempo real: %s',text)
        if self.on_status:await self.on_status(text)
    async def stop(self):
        self._stop_event.set()
        if self._socket is not None:
            try:await self._socket.close(code=1000,reason='Detenido')
            except Exception:pass
    async def _emit(self,tick):
        ts=tick.timestamp_ms
        if self._last_open_ms is not None and ts<self._last_open_ms:return
        if self._last_open_ms is not None and ts-self._last_open_ms>_interval_ms(self.timeframe) and self.on_gap:
            try:await self.on_gap(self._last_open_ms,ts)
            except Exception:logger.exception('Recuperación de huecos falló')
        self._last_open_ms=ts; await self.on_tick(tick)
    async def _run_ws_once(self,url):
        import websockets
        await self._status('Conectando WebSocket')
        async with websockets.connect(url,ping_interval=15,ping_timeout=10,close_timeout=3,open_timeout=5,max_queue=32,compression=None) as socket:
            self._socket=socket; await self._status('En vivo · WebSocket')
            while not self._stop_event.is_set():
                raw=await asyncio.wait_for(socket.recv(),timeout=25)
                k=json.loads(raw).get('k')
                if not k:continue
                await self._emit(RealtimeTick(self.symbol,self.timeframe,int(k['t']),float(k['o']),float(k['h']),float(k['l']),float(k['c']),float(k['v']),bool(k['x'])))
    async def _fetch_kline(self):
        import requests
        symbol=_stream_symbol(self.symbol).upper(); errors=[]
        for base in self.REST_BASES:
            try:
                response=await asyncio.to_thread(requests.get,f'{base}/api/v3/klines',params={'symbol':symbol,'interval':self.timeframe,'limit':2},timeout=5,headers={'User-Agent':'AEON-Mobile/9.2.0'})
                response.raise_for_status(); rows=response.json(); row=rows[-1]
                return RealtimeTick(self.symbol,self.timeframe,int(row[0]),float(row[1]),float(row[2]),float(row[3]),float(row[4]),float(row[5]),bool(int(row[6])<=__import__('time').time()*1000))
            except Exception as exc:errors.append(str(exc))
        raise RuntimeError(errors[-1] if errors else 'Sin respuesta REST')
    async def _run_rest(self):
        await self._status('En vivo · REST OHLCV')
        failures=0
        while not self._stop_event.is_set():
            try:
                await self._emit(await self._fetch_kline()); failures=0
            except Exception as exc:
                failures+=1; logger.warning('REST live falló: %s',exc); await self._status(f'Reintentando ({failures})')
            try:await asyncio.wait_for(self._stop_event.wait(),timeout=2.0)
            except asyncio.TimeoutError:pass
    async def run(self):
        stream=f'{_stream_symbol(self.symbol)}@kline_{self.timeframe}'
        for index,base in enumerate(self.WS_BASES,1):
            if self._stop_event.is_set():break
            try:
                await self._run_ws_once(f'{base}/{stream}')
                if self._stop_event.is_set():break
            except asyncio.CancelledError:break
            except Exception as exc:
                logger.warning('WebSocket %s falló: %s',base,exc)
                if not self._stop_event.is_set():await self._status(f'Canal alternativo {index}/3')
            finally:self._socket=None
        if not self._stop_event.is_set():await self._run_rest()
        self._socket=None; await self._status('Desconectado')
