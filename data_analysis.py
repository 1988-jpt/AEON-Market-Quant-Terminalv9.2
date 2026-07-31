"""Transformación de velas y cálculo de indicadores técnicos."""

from typing import List, Optional

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {"open", "high", "low", "close", "volume"}


def validate_ohlcv_dataframe(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas OHLCV: {', '.join(sorted(missing))}")
    if df.empty:
        raise ValueError("No hay datos para analizar.")


def ohlcv_to_df(ohlcv: List[List], tz: Optional[str] = None) -> pd.DataFrame:
    if not ohlcv:
        raise ValueError("La respuesta OHLCV está vacía.")

    df = pd.DataFrame(
        ohlcv,
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    if tz:
        df["timestamp"] = df["timestamp"].dt.tz_convert(tz)
    else:
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)

    numeric_columns = ["open", "high", "low", "close", "volume"]
    df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors="coerce")
    df.dropna(subset=numeric_columns, inplace=True)
    df.drop_duplicates(subset="timestamp", keep="last", inplace=True)
    df.sort_values("timestamp", inplace=True)
    df.set_index("timestamp", inplace=True)
    validate_ohlcv_dataframe(df)
    return df


def calculate_moving_average(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    if df.empty or "close" not in df.columns:
        raise ValueError("Se necesita una columna close con datos.")
    if period <= 0:
        raise ValueError("El período debe ser mayor que cero.")
    result = df.copy()
    result[f"ma_{period}"] = result["close"].rolling(window=period).mean()
    return result


def calculate_ema(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    if df.empty or "close" not in df.columns:
        raise ValueError("Se necesita una columna close con datos.")
    if period <= 0:
        raise ValueError("El período debe ser mayor que cero.")
    result = df.copy()
    result[f"ema_{period}"] = result["close"].ewm(span=period, adjust=False).mean()
    return result


def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    if df.empty or "close" not in df.columns:
        raise ValueError("Se necesita una columna close con datos.")
    if period <= 1:
        raise ValueError("El período RSI debe ser mayor que uno.")

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    average_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    average_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    relative_strength = average_gain / average_loss.replace(0, np.nan)
    result = 100 - (100 / (1 + relative_strength))
    return result.fillna(50.0)
