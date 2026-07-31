"""Servicio que coordina descarga, análisis técnico, noticias y almacenamiento."""
from __future__ import annotations
import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import pandas as pd

from advanced_strategy import AdvancedStrategy
from binance_client import BinanceClient
from config import OHLCV_LIMIT, OHLCV_TIMEFRAME
from data_analysis import ohlcv_to_df
from news_sentiment import NewsItem, fetch_news, summarize_sentiment
from storage import Storage

HIGHER_MAP = {'5m':'15m','15m':'1h','30m':'4h','1h':'4h','4h':'1d','1d':'1w'}

@dataclass(frozen=True)
class AnalysisResult:
    symbol: str
    timeframe: str
    price: float
    timestamp_ms: int
    decision: Dict[str, Any]
    dataframe: pd.DataFrame
    news: List[NewsItem]
    sentiment: Dict[str, Any]
    saved: bool

class MarketAnalyzerService:
    def __init__(self, db_path: Optional[str] = None, client: Optional[BinanceClient] = None):
        self.storage = Storage(db_path)
        self.client = client or BinanceClient()
        self.strategy = AdvancedStrategy()
        self._news_cache: Dict[str, tuple[float, List[NewsItem]]] = {}
        self._news_ttl_seconds = 300.0

    async def analyze(self, symbol: str, timeframe: str = OHLCV_TIMEFRAME,
                      limit: int = OHLCV_LIMIT, **_ignored) -> AnalysisResult:
        higher_tf = HIGHER_MAP.get(timeframe)
        normalized_symbol = symbol.strip().upper().replace('-', '/')
        cached_news = self._news_cache.get(normalized_symbol)
        news_fresh = cached_news and (time.monotonic() - cached_news[0] < self._news_ttl_seconds)
        news_task = asyncio.sleep(0, result=cached_news[1]) if news_fresh else fetch_news(normalized_symbol)
        tasks = [
            self.client.fetch_ohlcv(normalized_symbol, timeframe=timeframe, limit=limit),
            news_task,
        ]
        if higher_tf:
            tasks.append(self.client.fetch_ohlcv(symbol, timeframe=higher_tf,
                                                 limit=max(220, min(limit, 500))))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        if isinstance(results[0], Exception):
            raise results[0]
        dataframe = ohlcv_to_df(results[0])
        if len(dataframe) < 220:
            raise ValueError(f'Datos insuficientes: Binance devolvió {len(dataframe)} velas; se requieren al menos 220.')
        news = [] if isinstance(results[1], Exception) else results[1]
        if news and not news_fresh:
            self._news_cache[normalized_symbol] = (time.monotonic(), news)
        higher_df = None
        higher_warning = None
        if higher_tf and len(results) > 2 and not isinstance(results[2], Exception):
            higher_df = ohlcv_to_df(results[2])
            if len(higher_df) < 30:
                higher_warning = f'Temporalidad superior insuficiente ({len(higher_df)} velas)'
                higher_df = None
        elif higher_tf and len(results) > 2:
            higher_warning = f'No se pudo descargar temporalidad superior: {results[2]}'
        sentiment = summarize_sentiment(news)
        decision = self.strategy.decide(dataframe, sentiment['score'], higher_df)
        if higher_warning:
            decision.setdefault('warnings', []).append(higher_warning)
        analyzed_df = decision.pop('dataframe')
        price = float(analyzed_df['close'].iloc[-1])
        timestamp_ms = int(analyzed_df.index[-1].timestamp() * 1000)
        details = f"{decision.get('reason')} | Sentimiento: {sentiment['label']} | Confianza técnica: {decision.get('confidence')}%"
        saved = self.storage.insert_signal(timestamp_ms, normalized_symbol,
                                           decision['signal'], price, details)
        return AnalysisResult(normalized_symbol, timeframe, price, timestamp_ms,
                              decision, analyzed_df, news, sentiment, saved)

    async def close(self) -> None:
        await self.client.close()
