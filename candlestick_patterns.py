"""Detección explicable de patrones clásicos de velas japonesas."""

from typing import List
import pandas as pd


def detect_patterns(df: pd.DataFrame) -> List[str]:
    if len(df) < 3:
        return []
    a, b, c = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    body = abs(c['close'] - c['open'])
    candle_range = max(c['high'] - c['low'], 1e-12)
    upper = c['high'] - max(c['open'], c['close'])
    lower = min(c['open'], c['close']) - c['low']
    patterns: List[str] = []

    if body / candle_range <= 0.1:
        patterns.append('Doji')
    if lower >= body * 2 and upper <= max(body, candle_range * 0.1):
        patterns.append('Martillo')
    if upper >= body * 2 and lower <= max(body, candle_range * 0.1):
        patterns.append('Estrella fugaz')

    bullish_engulfing = b['close'] < b['open'] and c['close'] > c['open'] and c['open'] <= b['close'] and c['close'] >= b['open']
    bearish_engulfing = b['close'] > b['open'] and c['close'] < c['open'] and c['open'] >= b['close'] and c['close'] <= b['open']
    if bullish_engulfing:
        patterns.append('Envolvente alcista')
    if bearish_engulfing:
        patterns.append('Envolvente bajista')

    if a['close'] < a['open'] and abs(b['close'] - b['open']) < abs(a['close'] - a['open']) * 0.5 and c['close'] > c['open'] and c['close'] > (a['open'] + a['close']) / 2:
        patterns.append('Estrella de la mañana')
    if a['close'] > a['open'] and abs(b['close'] - b['open']) < abs(a['close'] - a['open']) * 0.5 and c['close'] < c['open'] and c['close'] < (a['open'] + a['close']) / 2:
        patterns.append('Estrella de la tarde')
    return patterns
