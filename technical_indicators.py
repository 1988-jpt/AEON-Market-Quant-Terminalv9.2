"""Indicadores técnicos avanzados calculados con pandas y NumPy."""

import numpy as np
import pandas as pd

from data_analysis import validate_ohlcv_dataframe


def add_advanced_indicators(df: pd.DataFrame) -> pd.DataFrame:
    validate_ohlcv_dataframe(df)
    out = df.copy()
    close, high, low, volume = out['close'], out['high'], out['low'], out['volume']

    out['ema_9'] = close.ewm(span=9, adjust=False).mean()
    out['ema_21'] = close.ewm(span=21, adjust=False).mean()
    out['ema_50'] = close.ewm(span=50, adjust=False).mean()
    out['sma_200'] = close.rolling(200).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    out['rsi'] = (100 - 100 / (1 + rs)).fillna(50)

    out['macd'] = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    out['macd_signal'] = out['macd'].ewm(span=9, adjust=False).mean()
    out['macd_hist'] = out['macd'] - out['macd_signal']

    middle = close.rolling(20).mean()
    std = close.rolling(20).std(ddof=0)
    out['bb_middle'] = middle
    out['bb_upper'] = middle + 2 * std
    out['bb_lower'] = middle - 2 * std

    previous_close = close.shift(1)
    true_range = pd.concat([
        high - low,
        (high - previous_close).abs(),
        (low - previous_close).abs(),
    ], axis=1).max(axis=1)
    out['atr'] = true_range.ewm(alpha=1/14, adjust=False).mean()

    lowest = low.rolling(14).min()
    highest = high.rolling(14).max()
    denominator = (highest - lowest).replace(0, np.nan)
    out['stoch_k'] = (100 * (close - lowest) / denominator).fillna(50)
    out['stoch_d'] = out['stoch_k'].rolling(3).mean().fillna(50)

    typical = (high + low + close) / 3
    cumulative_volume = volume.replace(0, np.nan).cumsum()
    out['vwap'] = (typical * volume).cumsum() / cumulative_volume

    direction = np.sign(close.diff()).fillna(0)
    out['obv'] = (direction * volume).cumsum()

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    atr_safe = out['atr'].replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_safe
    minus_di = 100 * minus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_safe
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    out['adx'] = dx.ewm(alpha=1/14, adjust=False).mean().fillna(0)
    out['plus_di'] = plus_di.fillna(0)
    out['minus_di'] = minus_di.fillna(0)

    return out


def add_quality_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Amplía indicadores con volumen relativo, ROC y eficiencia de tendencia."""
    out = add_advanced_indicators(df)
    volume_mean = out['volume'].rolling(20).mean()
    volume_std = out['volume'].rolling(20).std(ddof=0).replace(0, np.nan)
    out['volume_ratio'] = (out['volume'] / volume_mean.replace(0, np.nan)).fillna(1.0)
    out['volume_zscore'] = ((out['volume'] - volume_mean) / volume_std).fillna(0.0)
    out['roc_10'] = out['close'].pct_change(10).mul(100).fillna(0.0)
    change = out['close'].diff(10).abs()
    path = out['close'].diff().abs().rolling(10).sum().replace(0, np.nan)
    out['efficiency_ratio'] = (change / path).fillna(0.0).clip(0, 1)
    out['atr_pct'] = (out['atr'] / out['close'].replace(0, np.nan) * 100).fillna(0.0)
    out['obv_ema'] = out['obv'].ewm(span=21, adjust=False).mean()
    return out
