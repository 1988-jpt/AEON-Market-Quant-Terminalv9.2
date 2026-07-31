"""Fachada Binance asíncrona con backend público ligero o CCXT opcional."""
from __future__ import annotations
import asyncio
import logging
from typing import Optional

from config import BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_BACKEND
from binance_rest_client import BinancePublicRestClient

logger = logging.getLogger(__name__)


class BinanceClient:
    """Mantiene la interfaz histórica del proyecto y selecciona el backend.

    ``public_rest`` es el predeterminado: más rápido al iniciar y más sencillo
    para Android. ``ccxt`` permanece disponible para escritorio.
    """
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None,
                 backend: Optional[str] = None):
        self.api_key = api_key or BINANCE_API_KEY
        self.api_secret = api_secret or BINANCE_API_SECRET
        self.backend_name = (backend or BINANCE_BACKEND).lower()
        self._client = None

    async def _get_client(self):
        if self._client is not None:
            return self._client
        if self.backend_name != 'ccxt':
            self._client = BinancePublicRestClient()
            return self._client
        try:
            import ccxt.async_support as ccxt_async
        except ImportError as exc:
            logger.warning('CCXT no está instalado; usando REST público.')
            self.backend_name = 'public_rest'
            self._client = BinancePublicRestClient()
            return self._client
        opts = {'enableRateLimit': True, 'timeout': 30000,
                'options': {'defaultType': 'spot'}}
        if self.api_key:
            opts['apiKey'] = self.api_key
        if self.api_secret:
            opts['secret'] = self.api_secret
        exchange = ccxt_async.binance(opts)
        await exchange.load_markets()
        self._client = _CcxtAdapter(exchange)
        return self._client

    async def fetch_ohlcv(self, *args, **kwargs):
        return await (await self._get_client()).fetch_ohlcv(*args, **kwargs)

    async def fetch_ohlcv_history(self, *args, **kwargs):
        return await (await self._get_client()).fetch_ohlcv_history(*args, **kwargs)

    async def fetch_ohlcv_range(self, *args, **kwargs):
        client = await self._get_client()
        if hasattr(client, 'fetch_ohlcv_range'):
            return await client.fetch_ohlcv_range(*args, **kwargs)
        return await client.fetch_ohlcv_history(args[0], args[1], kwargs.get('since_ms'), kwargs.get('until_ms'), kwargs.get('limit', 1000))

    async def fetch_order_book(self, *args, **kwargs):
        client = await self._get_client()
        if not hasattr(client, 'fetch_order_book'):
            raise RuntimeError('El backend CCXT no expone profundidad en esta versión.')
        return await client.fetch_order_book(*args, **kwargs)

    async def close(self):
        if self._client is not None:
            await self._client.close()
            self._client = None


class _CcxtAdapter:
    def __init__(self, exchange):
        self.exchange = exchange

    async def fetch_ohlcv(self, symbol, timeframe='1h', limit=500, since=None, until=None):
        if limit <= 1000 and since is None and until is None:
            return await self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        return await self.fetch_ohlcv_history(symbol, timeframe, since, until, limit)

    async def fetch_ohlcv_history(self, symbol, timeframe, since=None, until=None,
                                  max_bars=10000, page_limit=1000):
        from binance_rest_client import _ms
        tf_ms = int(self.exchange.parse_timeframe(timeframe) * 1000)
        end = _ms(until) or self.exchange.milliseconds()
        start = _ms(since) or max(0, end - int(max_bars) * tf_ms)
        cursor, rows = start, {}
        while cursor <= end and len(rows) < int(max_bars):
            limit = min(int(page_limit), int(max_bars) - len(rows))
            batch = await self.exchange.fetch_ohlcv(symbol, timeframe=timeframe,
                                                    since=cursor, limit=limit)
            if not batch:
                break
            for row in batch:
                if int(row[0]) <= end:
                    rows[int(row[0])] = row
            nxt = int(batch[-1][0]) + tf_ms
            if nxt <= cursor:
                break
            cursor = nxt
            if len(batch) < limit:
                break
        return [rows[k] for k in sorted(rows)][-int(max_bars):]

    async def close(self):
        await self.exchange.close()


def fetch_ohlcv_sync(symbol, api_key=None, api_secret=None):
    async def _fetch():
        client = BinanceClient(api_key, api_secret)
        try:
            return await client.fetch_ohlcv(symbol)
        finally:
            await client.close()
    return asyncio.run(_fetch())
