"""Ejecución Spot aislada, con testnet por defecto y controles estrictos.

Importar este módulo nunca envía órdenes. Mainnet exige una política explícita,
una variable de entorno deliberada y una frase de confirmación diferente.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
import urllib.parse
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import requests

from operational_guardrails import GuardrailPolicy, OperationalGuardrails


@dataclass(frozen=True)
class ExecutionPolicy:
    max_notional_usdt: Decimal = Decimal("25")
    max_daily_loss_usdt: Decimal = Decimal("10")
    max_open_orders: int = 3
    allowed_symbols: tuple[str, ...] = ("BTCUSDT",)
    testnet_only: bool = True
    request_timeout_seconds: float = 10.0


class SafeSpotExecutionEngine:
    TESTNET = "https://testnet.binance.vision"
    MAINNET = "https://api.binance.com"

    def __init__(self, api_key: str, api_secret: str, policy: ExecutionPolicy = ExecutionPolicy(), session=None):
        if not api_key or not api_secret:
            raise ValueError("Faltan credenciales de ejecución.")
        self.key = api_key
        self.secret = api_secret.encode()
        self.policy = policy
        self.session = session or requests.Session()
        self.guardrails = OperationalGuardrails(
            GuardrailPolicy(
                max_notional_usdt=policy.max_notional_usdt,
                max_daily_loss_usdt=policy.max_daily_loss_usdt,
                max_open_orders=policy.max_open_orders,
                allowed_symbols=policy.allowed_symbols,
            )
        )

    @property
    def is_mainnet(self) -> bool:
        return os.getenv("AEON_ENABLE_MAINNET") == "I_UNDERSTAND_REAL_MONEY_RISK" and not self.policy.testnet_only

    @property
    def base_url(self) -> str:
        return self.MAINNET if self.is_mainnet else self.TESTNET

    def _signed(self, params):
        data = dict(params)
        data["timestamp"] = int(time.time() * 1000)
        query = urllib.parse.urlencode(data)
        data["signature"] = hmac.new(self.secret, query.encode(), hashlib.sha256).hexdigest()
        return data

    def validate_order(self, symbol, side, quantity, reference_price, confirmation, *, open_orders=0, request_id=None):
        required = "CONFIRM_REAL_MONEY_ORDER" if self.is_mainnet else "CONFIRM_TESTNET_ORDER"
        if confirmation != required:
            raise PermissionError("Confirmación de seguridad inválida para el entorno seleccionado.")
        normalized, normalized_side, qty, _ = self.guardrails.validate(
            symbol=symbol,
            side=side,
            quantity=quantity,
            reference_price=reference_price,
            open_orders=open_orders,
            request_id=request_id,
        )
        return normalized, normalized_side, qty

    def _request(self, method, path, params=None):
        signed = self._signed(params or {})
        response = self.session.request(
            method,
            self.base_url + path,
            params=signed,
            headers={"X-MBX-APIKEY": self.key},
            timeout=self.policy.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, (dict, list)):
            raise RuntimeError("Respuesta inesperada del exchange.")
        return payload

    def market_order(self, symbol, side, quantity, reference_price, confirmation="", client_order_id: Optional[str] = None, *, open_orders=0):
        request_id = str(client_order_id)[:36] if client_order_id else None
        normalized, normalized_side, qty = self.validate_order(
            symbol, side, quantity, reference_price, confirmation,
            open_orders=open_orders, request_id=request_id,
        )
        data = {"symbol": normalized, "side": normalized_side, "type": "MARKET", "quantity": format(qty, "f"), "recvWindow": 5000}
        if request_id:
            data["newClientOrderId"] = request_id
        return self._request("POST", "/api/v3/order", data)

    def register_realized_pnl(self, pnl_usdt) -> None:
        self.guardrails.register_realized_pnl(pnl_usdt)

    def get_order(self, symbol, client_order_id):
        return self._request("GET", "/api/v3/order", {"symbol": self.guardrails.normalize_symbol(symbol), "origClientOrderId": client_order_id, "recvWindow": 5000})

    def open_orders(self, symbol):
        return self._request("GET", "/api/v3/openOrders", {"symbol": self.guardrails.normalize_symbol(symbol), "recvWindow": 5000})

    def cancel_order(self, symbol, client_order_id):
        return self._request("DELETE", "/api/v3/order", {"symbol": self.guardrails.normalize_symbol(symbol), "origClientOrderId": client_order_id, "recvWindow": 5000})

    def account(self):
        return self._request("GET", "/api/v3/account", {"recvWindow": 5000})
