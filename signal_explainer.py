"""Explicación estructurada y transparente de señales."""
from __future__ import annotations

def explain(decision: dict) -> dict:
    positives, risks = [], []
    signal = decision.get('signal', 'HOLD')
    regime = decision.get('market_regime', {})
    mtf = decision.get('higher_timeframe', {})
    if signal == 'BUY': positives.append('Sesgo comprador domina las confirmaciones independientes.')
    elif signal == 'SELL': positives.append('Sesgo vendedor domina las confirmaciones independientes.')
    else: risks.append('No existe una ventaja técnica suficiente para abrir una operación.')
    if regime.get('regime') in ('tendencia_alcista','tendencia_bajista'): positives.append(f"Régimen detectado: {regime.get('regime').replace('_',' ')}.")
    if mtf.get('bias') and mtf.get('bias') != 'neutral': positives.append(f"Temporalidad superior: {mtf.get('bias')} ({mtf.get('strength','sin fuerza')}).")
    if decision.get('adx', 0) >= 23: positives.append(f"ADX {decision.get('adx',0):.1f}: tendencia con fuerza operable.")
    if decision.get('volume_ratio', 0) >= 1.15: positives.append(f"Volumen relativo {decision.get('volume_ratio',0):.2f}x confirma participación.")
    if decision.get('patterns'): positives.append('Patrones: ' + ', '.join(decision['patterns'][:3]) + '.')
    for warning in decision.get('warnings', [])[:6]: risks.append(warning + '.')
    plan = decision.get('trade_plan') or {}
    return {'positives': positives[:6], 'risks': risks[:6], 'plan': plan,
            'summary': decision.get('reason', 'Sin explicación disponible.')}
