"""Cálculo robusto de soportes y resistencias recientes."""

from typing import Dict, List
import numpy as np
import pandas as pd


def _cluster(values: List[float], tolerance: float) -> List[float]:
    levels: List[float] = []
    for value in sorted(values):
        if not levels or abs(value - levels[-1]) / max(abs(levels[-1]), 1e-12) > tolerance:
            levels.append(float(value))
        else:
            levels[-1] = (levels[-1] + float(value)) / 2
    return levels


def calculate_levels(df: pd.DataFrame, window: int = 5, tolerance: float = 0.006) -> Dict[str, List[float]]:
    if len(df) < window * 2 + 1:
        return {'supports': [], 'resistances': []}
    lows = df['low']
    highs = df['high']
    support_candidates = lows[(lows == lows.rolling(window * 2 + 1, center=True).min())].dropna().tolist()
    resistance_candidates = highs[(highs == highs.rolling(window * 2 + 1, center=True).max())].dropna().tolist()
    price = float(df['close'].iloc[-1])
    supports = [x for x in _cluster(support_candidates, tolerance) if x < price][-3:]
    resistances = [x for x in _cluster(resistance_candidates, tolerance) if x > price][:3]
    return {'supports': supports, 'resistances': resistances}
