"""Cliente Binance público ligero, apto para escritorio y Android.

No requiere API keys ni CCXT. Las peticiones bloqueantes de requests se ejecutan
con asyncio.to_thread para no bloquear el event loop de Kivy.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional, Union

import requests
try:
    from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
except ImportError:  # Permite diagnóstico básico antes de instalar requirements.
    def retry(*_args, **_kwargs):
        return lambda fn: fn
    def retry_if_exception_type(*_args, **_kwargs): return None
    def stop_after_attempt(*_args, **_kwargs): return None
    def wait_exponential(*_args, **_kwargs): return None

from config import OHLCV_LIMIT, OHLCV_TIMEFRAME, VALID_TIMEFRAMES
from rate_limiter import RateLimiter

logger = logging.getLogger(__name__)
DateLike = Union[str, int, float, datetime, None]
BASE_URLS = (
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
)
TIMEFRAME_MS = {
    '1m': 60_000, '3m': 180_000, '5m': 300_000, '15m': 900_000,
    '30m': 1_800_000, '1h': 3_600_000, '2h': 7_200_000,
    '4h': 14_400_000, '6h': 21_600_000, '8h': 28_800_000,
    '12h': 43_200_000, '1d': 86_400_000, '3d': 259_200_000,
    '1w': 604_800_000,
}


def _ms(value: DateLike) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    text = str(value).strip().replace('Z', '+00:00')
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


class BinancePublicRestClient:
    def __init__(self, timeout: float = 25.0):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'AEON-Market-Terminal/4.0'})
        self.rate_limiter = RateLimiter(calls_per_second=4.0)
        self._closed = False

    @staticmethod
    def _validate(symbol: str, timeframe: str) -> str:
        normalized = symbol.strip().upper().replace('-', '/').replace('_', '/')
        if '/' not in normalized:
            raise ValueError('El símbolo debe tener el formato BTC/USDT.')
        if timeframe not in VALID_TIMEFRAMES:
            raise ValueError(f'Temporalidad no compatible: {timeframe}')
        return normalized

    @staticmethod
    def _binance_symbol(symbol: str) -> str:
        return symbol.replace('/', '')

    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(4),
           retry=retry_if_exception_type((requests.RequestException, TimeoutError)), reraise=True)
    def _get_page_sync(self, symbol: str, timeframe: str, start: Optional[int],
                       end: Optional[int], limit: int) -> List[list]:
        if self._closed:
            raise RuntimeError('El cliente Binance está cerrado.')
        params = {'symbol': self._binance_symbol(symbol), 'interval': timeframe,
                  'limit': max(1, min(int(limit), 1000))}
        if start is not None:
            params['startTime'] = int(start)
        if end is not None:
            params['endTime'] = int(end)
        last_error = None
        payload = None
        for base_url in BASE_URLS:
            try:
                response = self.session.get(f'{base_url}/api/v3/klines', params=params,
                                            timeout=self.timeout)
                response.raise_for_status()
                payload = response.json()
                break
            except requests.RequestException as exc:
                last_error = exc
                logger.warning('Endpoint Binance no disponible %s: %s', base_url, exc)
        if payload is None:
            raise RuntimeError(f'No se pudo conectar con Binance. Revisa Internet, DNS o bloqueo regional. Detalle: {last_error}')
        if isinstance(payload, dict):
            raise RuntimeError(payload.get('msg') or f'Respuesta inesperada de Binance: {payload}')
        return [[int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])]
                for r in payload]

    async def _fetch_page(self, symbol: str, timeframe: str, start: Optional[int],
                          end: Optional[int], limit: int) -> List[list]:
        await self.rate_limiter.wait_async()
        return await asyncio.to_thread(self._get_page_sync, symbol, timeframe, start, end, limit)

    async def fetch_ohlcv(self, symbol: str, timeframe: str = OHLCV_TIMEFRAME,
                          limit: int = OHLCV_LIMIT, since: DateLike = None,
                          until: DateLike = None) -> List[list]:
        normalized = self._validate(symbol, timeframe)
        if int(limit) < 30:
            raise ValueError('El límite de velas debe ser de al menos 30.')
        if int(limit) <= 1000 and since is None and until is None:
            return await self._fetch_page(normalized, timeframe, None, None, int(limit))
        return await self.fetch_ohlcv_history(normalized, timeframe, since, until, int(limit))

    async def fetch_ohlcv_history(self, symbol: str, timeframe: str,
                                  since: DateLike = None, until: DateLike = None,
                                  max_bars: int = 10_000, page_limit: int = 1000) -> List[list]:
        normalized = self._validate(symbol, timeframe)
        tf_ms = TIMEFRAME_MS[timeframe]
        end = _ms(until) or int(datetime.now(timezone.utc).timestamp() * 1000)
        start = _ms(since)
        if start is None:
            start = max(0, end - int(max_bars) * tf_ms)
        cursor = start
        rows: dict[int, list] = {}
        pages = 0
        while cursor <= end and len(rows) < int(max_bars):
            request_limit = min(int(page_limit), int(max_bars) - len(rows))
            batch = await self._fetch_page(normalized, timeframe, cursor, end, request_limit)
            pages += 1
            if not batch:
                break
            for row in batch:
                if int(row[0]) <= end:
                    rows[int(row[0])] = row
            next_cursor = int(batch[-1][0]) + tf_ms
            if next_cursor <= cursor:
                logger.warning('Paginación detenida por cursor repetido en %s %s', normalized, timeframe)
                break
            cursor = next_cursor
            if len(batch) < request_limit:
                break
        result = [rows[k] for k in sorted(rows) if start <= k <= end]
        logger.info('REST público %s %s: %s velas en %s páginas', normalized, timeframe,
                    len(result), pages)
        return result[-int(max_bars):]


    async def fetch_ohlcv_range(self, symbol: str, timeframe: str, since_ms: int, until_ms: int, limit: int = 1000) -> List[list]:
        return await self.fetch_ohlcv_history(symbol, timeframe, since_ms, until_ms, max_bars=limit)

    async def fetch_order_book(self, symbol: str, limit: int = 100) -> dict:
        normalized = self._validate(symbol, '1m')
        def get():
            last_error = None
            for base_url in BASE_URLS:
                try:
                    response = self.session.get(f'{base_url}/api/v3/depth', params={'symbol': self._binance_symbol(normalized), 'limit': max(5, min(int(limit), 5000))}, timeout=self.timeout)
                    response.raise_for_status()
                    return response.json()
                except requests.RequestException as exc:
                    last_error = exc
            raise RuntimeError(f'No se pudo consultar profundidad de Binance: {last_error}')
        await self.rate_limiter.wait_async()
        return await asyncio.to_thread(get)

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            await asyncio.to_thread(self.session.close)
