"""Normaliza funding, interés abierto, liquidaciones y profundidad para la estrategia."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable, Optional

@dataclass(frozen=True)
class DerivativesContext:
    funding_rate: float = 0.0
    open_interest_change_pct: float = 0.0
    liquidation_buy_usdt: float = 0.0
    liquidation_sell_usdt: float = 0.0
    order_book_imbalance: float = 0.0
    spread_bps: float = 0.0

    def validate(self) -> "DerivativesContext":
        vals = asdict(self)
        if any(not isinstance(v, (int, float)) for v in vals.values()):
            raise TypeError('El contexto de derivados contiene valores no numéricos.')
        return self

def score_derivatives(ctx: Optional[DerivativesContext]) -> dict:
    if ctx is None:
        return {'long': 0.0, 'short': 0.0, 'warnings': [], 'reasons_long': [], 'reasons_short': []}
    ctx.validate(); long = short = 0.0; warnings=[]; rl=[]; rs=[]
    # Funding extremo suele ser contrarian; OI confirma presión si acompaña.
    if ctx.funding_rate >= 0.0008:
        short += 0.55; warnings.append('Funding positivo elevado')
    elif ctx.funding_rate <= -0.0008:
        long += 0.55; warnings.append('Funding negativo elevado')
    if ctx.open_interest_change_pct > 2.0:
        long += 0.25; short += 0.25
    elif ctx.open_interest_change_pct < -3.0:
        warnings.append('Interés abierto en contracción')
    liq_total = ctx.liquidation_buy_usdt + ctx.liquidation_sell_usdt
    if liq_total > 0:
        imbalance = (ctx.liquidation_sell_usdt - ctx.liquidation_buy_usdt) / liq_total
        if imbalance > 0.35:
            long += 0.45; rl.append('Cascada de liquidaciones vendedoras potencialmente agotada')
        elif imbalance < -0.35:
            short += 0.45; rs.append('Cascada de liquidaciones compradoras potencialmente agotada')
    if ctx.order_book_imbalance > 0.20:
        long += 0.35; rl.append('Profundidad compradora dominante')
    elif ctx.order_book_imbalance < -0.20:
        short += 0.35; rs.append('Profundidad vendedora dominante')
    if ctx.spread_bps > 12:
        long -= 0.35; short -= 0.35; warnings.append('Spread elevado')
    return {'long': long, 'short': short, 'warnings': warnings, 'reasons_long': rl, 'reasons_short': rs}
