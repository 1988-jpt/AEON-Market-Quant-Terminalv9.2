"""Simulación Monte Carlo sobre secuencias de operaciones históricas."""
from __future__ import annotations
from typing import Any, Iterable
import numpy as np


def run_monte_carlo(trades: Iterable[dict[str, Any]], initial_capital: float,
                    simulations: int = 1000, seed: int = 42) -> dict[str, Any]:
    pnls = np.asarray([float(t.get('net_pnl', 0) or 0) for t in trades], dtype=float)
    simulations = max(100, min(int(simulations), 20_000))
    if len(pnls) < 2:
        return {'simulations': simulations, 'samples': int(len(pnls)), 'available': False}
    rng = np.random.default_rng(seed)
    final_capitals = np.empty(simulations)
    max_drawdowns = np.empty(simulations)
    ruin = 0
    for idx in range(simulations):
        sequence = rng.choice(pnls, size=len(pnls), replace=True)
        equity = float(initial_capital) + np.cumsum(sequence)
        full = np.concatenate(([float(initial_capital)], equity))
        peaks = np.maximum.accumulate(full)
        drawdowns = np.divide(full - peaks, peaks, out=np.zeros_like(full), where=peaks != 0) * 100
        final_capitals[idx] = full[-1]
        max_drawdowns[idx] = abs(float(drawdowns.min()))
        ruin += bool(np.any(full <= 0))
    percentile = lambda arr, p: round(float(np.percentile(arr, p)), 2)
    return {
        'available': True,
        'simulations': simulations,
        'samples': int(len(pnls)),
        'final_capital_p05': percentile(final_capitals, 5),
        'final_capital_median': percentile(final_capitals, 50),
        'final_capital_p95': percentile(final_capitals, 95),
        'max_drawdown_p50': percentile(max_drawdowns, 50),
        'max_drawdown_p95': percentile(max_drawdowns, 95),
        'risk_of_ruin_pct': round(ruin / simulations * 100, 3),
    }
