"""Profundidad de mercado y métricas de microestructura."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class OrderBookMetrics:
    best_bid:float; best_ask:float; spread:float; spread_bps:float; bid_depth:float; ask_depth:float; imbalance:float; mid_price:float

def analyze_order_book(bids:Iterable,asks:Iterable,levels:int=20)->OrderBookMetrics:
    b=[(float(p),float(q)) for p,q,*_ in list(bids)[:levels]]; a=[(float(p),float(q)) for p,q,*_ in list(asks)[:levels]]
    if not b or not a: raise ValueError('Libro de órdenes vacío.')
    bb,ba=b[0][0],a[0][0]
    if ba<bb: raise ValueError('Libro cruzado o inválido.')
    bd=sum(p*q for p,q in b); ad=sum(p*q for p,q in a); total=bd+ad; mid=(bb+ba)/2; spread=ba-bb
    return OrderBookMetrics(bb,ba,spread,(spread/mid)*10000 if mid else 0,bd,ad,(bd-ad)/total if total else 0,mid)
