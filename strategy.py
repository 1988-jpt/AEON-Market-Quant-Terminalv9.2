"""Estrategias de análisis. No ejecutan órdenes ni garantizan resultados."""

import logging
from typing import Any, Dict

import pandas as pd

from data_analysis import calculate_moving_average, rsi, validate_ohlcv_dataframe

logger = logging.getLogger(__name__)


class StrategyBase:
    def decide(self, df: pd.DataFrame) -> Dict[str, Any]:
        raise NotImplementedError


class MaCrossStrategy(StrategyBase):
    """Cruce de medias con filtro RSI para reducir señales débiles."""

    def __init__(self, short_period: int = 5, long_period: int = 20, rsi_period: int = 14):
        if short_period <= 0 or long_period <= 0:
            raise ValueError("Los períodos deben ser mayores que cero.")
        if short_period >= long_period:
            raise ValueError("La media corta debe ser menor que la media larga.")
        self.short_period = short_period
        self.long_period = long_period
        self.rsi_period = rsi_period

    def decide(self, df: pd.DataFrame) -> Dict[str, Any]:
        validate_ohlcv_dataframe(df)
        minimum_rows = max(self.long_period + 2, self.rsi_period + 2)
        if len(df) < minimum_rows:
            return {
                "signal": "HOLD",
                "reason": f"Datos insuficientes: se necesitan al menos {minimum_rows} velas.",
            }

        analyzed = calculate_moving_average(df, self.short_period)
        analyzed = calculate_moving_average(analyzed, self.long_period)
        analyzed["rsi"] = rsi(analyzed, self.rsi_period)

        short_name = f"ma_{self.short_period}"
        long_name = f"ma_{self.long_period}"
        last = analyzed.iloc[-1]
        previous = analyzed.iloc[-2]

        crossed_up = previous[short_name] <= previous[long_name] and last[short_name] > last[long_name]
        crossed_down = previous[short_name] >= previous[long_name] and last[short_name] < last[long_name]
        current_rsi = float(last["rsi"])

        if crossed_up and current_rsi < 70:
            signal = "BUY"
            reason = "Cruce alcista de medias confirmado por RSI."
        elif crossed_down and current_rsi > 30:
            signal = "SELL"
            reason = "Cruce bajista de medias confirmado por RSI."
        elif crossed_up:
            signal = "HOLD"
            reason = "Cruce alcista, pero el RSI indica posible sobrecompra."
        elif crossed_down:
            signal = "HOLD"
            reason = "Cruce bajista, pero el RSI indica posible sobreventa."
        else:
            signal = "HOLD"
            reason = "No se detectó un cruce nuevo de medias."

        return {
            "signal": signal,
            "reason": reason,
            "short_ma": float(last[short_name]),
            "long_ma": float(last[long_name]),
            "rsi": current_rsi,
        }
