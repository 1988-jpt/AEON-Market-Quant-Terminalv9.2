"""Calibración empírica de la calidad técnica usando operaciones históricas."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable, Any


@dataclass(frozen=True)
class CalibrationBucket:
    minimum: float
    maximum: float
    samples: int
    wins: int
    win_rate_pct: float
    avg_return_pct: float


def calibrate_confidence(trades: Iterable[dict[str, Any]], bucket_size: int = 5,
                         minimum_samples: int = 10) -> dict[str, Any]:
    size = max(1, int(bucket_size))
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for trade in trades:
        confidence = float(trade.get('confidence', 0) or 0)
        lower = int(confidence // size) * size
        key = (lower, min(100, lower + size))
        grouped.setdefault(key, []).append(trade)
    buckets = []
    for (low, high), items in sorted(grouped.items()):
        wins = sum(float(item.get('net_pnl', 0) or 0) > 0 for item in items)
        returns = [float(item.get('return_pct', 0) or 0) for item in items]
        bucket = CalibrationBucket(low, high, len(items), wins,
                                   round(wins / len(items) * 100, 2),
                                   round(sum(returns) / len(returns), 4))
        buckets.append(asdict(bucket))
    reliable = [b for b in buckets if b['samples'] >= int(minimum_samples)]
    return {
        'bucket_size': size,
        'minimum_samples': int(minimum_samples),
        'buckets': buckets,
        'reliable_buckets': reliable,
        'calibrated': bool(reliable),
    }
