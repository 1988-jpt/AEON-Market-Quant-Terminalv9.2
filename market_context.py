"""Clasificación de régimen, divergencias y calidad del mercado sin IA."""
from __future__ import annotations

from typing import Any, Dict, Optional
import numpy as np
import pandas as pd


def classify_regime(df: pd.DataFrame) -> Dict[str, Any]:
    last = df.iloc[-1]
    close = df['close']
    atr_pct = float(last['atr'] / last['close'] * 100) if last['close'] else 0.0
    bb_width = float((last['bb_upper'] - last['bb_lower']) / last['bb_middle'] * 100) if last['bb_middle'] else 0.0
    slope = float(close.pct_change(10).iloc[-1] * 100) if len(df) > 10 else 0.0
    adx = float(last['adx'])

    if atr_pct >= 4.0 or bb_width >= 12.0:
        volatility = 'extrema'
    elif atr_pct >= 2.0 or bb_width >= 7.0:
        volatility = 'alta'
    elif atr_pct <= 0.45 and bb_width <= 2.0:
        volatility = 'baja'
    else:
        volatility = 'normal'

    if adx >= 25 and last['ema_21'] > last['ema_50'] and slope > 0:
        regime = 'tendencia_alcista'
    elif adx >= 25 and last['ema_21'] < last['ema_50'] and slope < 0:
        regime = 'tendencia_bajista'
    elif adx < 18:
        regime = 'lateral'
    else:
        regime = 'transicion'
    return {'regime': regime, 'volatility': volatility, 'atr_pct': round(atr_pct, 3),
            'bb_width_pct': round(bb_width, 3), 'slope_10_pct': round(slope, 3)}


def detect_divergence(df: pd.DataFrame, lookback: int = 24) -> str:
    """Divergencia aproximada usando regresión de precio y RSI."""
    window = df[['close', 'rsi']].dropna().tail(lookback)
    if len(window) < 12:
        return 'ninguna'
    x = np.arange(len(window), dtype=float)
    price_slope = np.polyfit(x, window['close'].to_numpy(dtype=float), 1)[0]
    rsi_slope = np.polyfit(x, window['rsi'].to_numpy(dtype=float), 1)[0]
    price_norm = price_slope / max(abs(float(window['close'].mean())), 1e-9)
    if price_norm < -0.0005 and rsi_slope > 0.08:
        return 'alcista'
    if price_norm > 0.0005 and rsi_slope < -0.08:
        return 'bajista'
    return 'ninguna'


def higher_timeframe_bias(df: Optional[pd.DataFrame]) -> Dict[str, Any]:
    if df is None or len(df) < 60:
        return {'bias': 'neutral', 'confirmed': False, 'strength': 'ninguna'}
    last = df.iloc[-1]
    if last['ema_21'] > last['ema_50'] and last['close'] > last['ema_50']:
        strength = 'fuerte' if last['macd_hist'] > 0 and last['adx'] >= 20 else 'moderada'
        return {'bias': 'alcista', 'confirmed': True, 'strength': strength}
    if last['ema_21'] < last['ema_50'] and last['close'] < last['ema_50']:
        strength = 'fuerte' if last['macd_hist'] < 0 and last['adx'] >= 20 else 'moderada'
        return {'bias': 'bajista', 'confirmed': True, 'strength': strength}
    return {'bias': 'neutral', 'confirmed': False, 'strength': 'ninguna'}
