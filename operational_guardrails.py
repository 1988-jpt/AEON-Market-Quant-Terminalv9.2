"""Controles operativos reutilizables para paper trading y ejecución Spot.

El módulo no envía órdenes. Centraliza límites, bloqueo de duplicados y estado de
pérdida diaria para que la interfaz y el motor de ejecución apliquen las mismas reglas.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class GuardrailPolicy:
    max_notional_usdt: Decimal = Decimal("25")
    max_daily_loss_usdt: Decimal = Decimal("10")
    max_open_orders: int = 3
    duplicate_window_seconds: float = 15.0
    allowed_symbols: Tuple[str, ...] = ("BTCUSDT",)


class OperationalGuardrails:
    """Estado seguro, thread-safe y reiniciable por día UTC."""

    def __init__(self, policy: GuardrailPolicy = GuardrailPolicy(), clock=time.time):
        self.policy = policy
        self._clock = clock
        self._lock = threading.RLock()
        self._daily_loss = Decimal("0")
        self._day = self._utc_day()
        self._recent: Dict[str, float] = {}

    def _utc_day(self) -> int:
        return int(self._clock() // 86400)

    def _roll_day(self) -> None:
        day = self._utc_day()
        if day != self._day:
            self._day = day
            self._daily_loss = Decimal("0")
            self._recent.clear()

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        return str(symbol).replace("/", "").replace("-", "").upper().strip()

    def register_realized_pnl(self, pnl_usdt: Decimal | float | str) -> None:
        with self._lock:
            self._roll_day()
            pnl = Decimal(str(pnl_usdt))
            if pnl < 0:
                self._daily_loss += -pnl

    @property
    def daily_loss(self) -> Decimal:
        with self._lock:
            self._roll_day()
            return self._daily_loss

    def validate(
        self,
        *,
        symbol: str,
        side: str,
        quantity: Decimal | float | str,
        reference_price: Decimal | float | str,
        open_orders: int = 0,
        request_id: Optional[str] = None,
    ) -> tuple[str, str, Decimal, Decimal]:
        with self._lock:
            self._roll_day()
            normalized = self.normalize_symbol(symbol)
            normalized_side = str(side).upper().strip()
            qty = Decimal(str(quantity))
            price = Decimal(str(reference_price))
            notional = qty * price

            if normalized not in self.policy.allowed_symbols:
                raise PermissionError("Símbolo no autorizado por la lista blanca.")
            if normalized_side not in {"BUY", "SELL"}:
                raise ValueError("El lado debe ser BUY o SELL.")
            if qty <= 0 or price <= 0:
                raise ValueError("Cantidad y precio deben ser positivos.")
            if notional > self.policy.max_notional_usdt:
                raise PermissionError("El valor de la orden supera el límite permitido.")
            if self._daily_loss >= self.policy.max_daily_loss_usdt:
                raise PermissionError("Se alcanzó el límite de pérdida diaria.")
            if int(open_orders) >= self.policy.max_open_orders:
                raise PermissionError("Se alcanzó el máximo de órdenes abiertas.")

            if request_id:
                now = self._clock()
                expiry = now - self.policy.duplicate_window_seconds
                self._recent = {key: ts for key, ts in self._recent.items() if ts >= expiry}
                if request_id in self._recent:
                    raise PermissionError("Orden duplicada bloqueada.")
                self._recent[request_id] = now

            return normalized, normalized_side, qty, notional
