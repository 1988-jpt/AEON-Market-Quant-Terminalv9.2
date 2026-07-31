"""Niveles orientativos de riesgo basados en ATR y estructura técnica."""
from __future__ import annotations
from typing import Any, Dict, Iterable


def _nearest(values: Iterable[float], price: float, below: bool):
    valid = [float(v) for v in values if (float(v) < price if below else float(v) > price)]
    if not valid:
        return None
    return max(valid) if below else min(valid)


def build_trade_plan(signal: str, price: float, atr: float, supports, resistances) -> Dict[str, Any]:
    if signal == 'HOLD' or atr <= 0:
        return {'entry': price, 'stop_loss': None, 'take_profit_1': None,
                'take_profit_2': None, 'risk_reward': None}
    if signal == 'BUY':
        structural = _nearest(supports, price, True)
        atr_stop = price - 1.6 * atr
        stop = min(atr_stop, structural - 0.25 * atr) if structural else atr_stop
        risk = price - stop
        tp1, tp2 = price + 1.5 * risk, price + 2.5 * risk
    else:
        structural = _nearest(resistances, price, False)
        atr_stop = price + 1.6 * atr
        stop = max(atr_stop, structural + 0.25 * atr) if structural else atr_stop
        risk = stop - price
        tp1, tp2 = price - 1.5 * risk, price - 2.5 * risk
    return {'entry': round(price, 8), 'stop_loss': round(stop, 8),
            'take_profit_1': round(tp1, 8), 'take_profit_2': round(tp2, 8),
            'risk_reward': 2.5}
