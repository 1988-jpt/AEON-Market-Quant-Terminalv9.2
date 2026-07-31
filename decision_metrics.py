"""Métricas derivadas y explicables para presentar una decisión técnica.

No pretende estimar probabilidades estadísticas reales. Convierte el balance de
puntuaciones del motor en un indicador visual normalizado para la interfaz.
"""
from __future__ import annotations

import math
from typing import Any, Dict


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def derive_decision_metrics(decision: Dict[str, Any], price: float) -> Dict[str, Any]:
    long_score = float(decision.get("long_score", 0.0) or 0.0)
    short_score = float(decision.get("short_score", 0.0) or 0.0)
    confidence = _clamp(decision.get("confidence", 50.0) or 50.0, 0.0, 100.0)
    atr = max(0.0, float(decision.get("atr", 0.0) or 0.0))
    atr_pct = (atr / price * 100.0) if price > 0 else 0.0

    # Softmax estable para representar el balance relativo de evidencia.
    scale = 2.25
    a = _clamp(long_score / scale, -20.0, 20.0)
    b = _clamp(short_score / scale, -20.0, 20.0)
    ea, eb = math.exp(a), math.exp(b)
    buy_probability = 100.0 * ea / max(ea + eb, 1e-12)
    sell_probability = 100.0 - buy_probability

    warnings = decision.get("warnings") or []
    volatility = (decision.get("market_regime") or {}).get("volatility", "normal")
    risk_points = atr_pct * 8.0 + len(warnings) * 4.0
    if volatility == "alta":
        risk_points += 14.0
    elif volatility == "extrema":
        risk_points += 30.0
    if confidence < 65:
        risk_points += (65.0 - confidence) * 0.5
    risk_points = _clamp(risk_points, 0.0, 100.0)
    if risk_points < 28:
        risk_level = "BAJO"
    elif risk_points < 52:
        risk_level = "MEDIO"
    elif risk_points < 74:
        risk_level = "ALTO"
    else:
        risk_level = "MUY ALTO"

    signal = str(decision.get("signal", "HOLD"))
    dominant_probability = buy_probability if signal == "BUY" else sell_probability if signal == "SELL" else max(buy_probability, sell_probability)
    return {
        "buy_probability": round(buy_probability, 1),
        "buy_evidence": round(buy_probability, 1),
        "sell_probability": round(sell_probability, 1),
        "sell_evidence": round(sell_probability, 1),
        "dominant_probability": round(dominant_probability, 1),
        "risk_score": round(risk_points, 1),
        "risk_level": risk_level,
        "atr_pct": round(atr_pct, 3),
        "label": "Evidencia técnica normalizada; no es una probabilidad estadística ni una garantía de ganancia.",
    }
