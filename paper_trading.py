"""Motor de paper trading persistente; nunca envía órdenes reales."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class PaperPosition:
    symbol: str
    side: str
    entry: float
    quantity: float
    stop: float
    target: float
    opened_at: str
    confidence: float


class PaperTradingEngine:
    def __init__(self, storage, initial_balance: float = 10_000.0,
                 fee_rate: float = 0.001, risk_per_trade: float = 0.01):
        self.storage = storage
        self.initial_balance = float(initial_balance)
        self.fee_rate = max(0.0, float(fee_rate))
        self.risk_per_trade = max(0.001, min(float(risk_per_trade), 0.05))
        self.storage.ensure_paper_account(self.initial_balance)

    def account(self) -> dict[str, Any]:
        return self.storage.get_paper_account()

    def open_from_decision(self, symbol: str, price: float, decision: dict[str, Any]) -> Optional[int]:
        signal = decision.get('signal')
        if signal not in ('BUY', 'SELL'):
            return None
        if self.storage.get_open_paper_position(symbol):
            raise ValueError(f'Ya existe una posición paper abierta para {symbol}.')
        plan = decision.get('trade_plan') or {}
        stop = float(plan.get('stop_loss') or 0)
        target = float(plan.get('take_profit_2') or plan.get('take_profit_1') or 0)
        if signal == 'BUY' and not (0 < stop < price < target):
            raise ValueError('Plan LONG inválido para paper trading.')
        if signal == 'SELL' and not (target < price < stop):
            raise ValueError('Plan SHORT inválido para paper trading.')
        account = self.account()
        risk_cash = float(account['balance']) * self.risk_per_trade
        distance = abs(float(price) - stop)
        quantity = risk_cash / distance if distance > 0 else 0
        quantity = min(quantity, float(account['balance']) / float(price))
        if quantity * price < 10:
            raise ValueError('Capital insuficiente para una operación paper mínima.')
        position = PaperPosition(symbol.upper(), 'LONG' if signal == 'BUY' else 'SHORT',
                                 float(price), quantity, stop, target,
                                 datetime.now(timezone.utc).isoformat(),
                                 float(decision.get('confidence', 0) or 0))
        return self.storage.open_paper_position(asdict(position))

    def mark(self, symbol: str, price: float) -> Optional[dict[str, Any]]:
        position = self.storage.get_open_paper_position(symbol)
        if not position:
            return None
        side = position['side']
        stop_hit = price <= position['stop'] if side == 'LONG' else price >= position['stop']
        target_hit = price >= position['target'] if side == 'LONG' else price <= position['target']
        if stop_hit or target_hit:
            return self.close(symbol, price, 'stop_loss' if stop_hit else 'take_profit')
        direction = 1 if side == 'LONG' else -1
        unrealized = (float(price) - position['entry']) * position['quantity'] * direction
        return {**position, 'unrealized_pnl': unrealized, 'mark_price': float(price)}

    def close(self, symbol: str, price: float, reason: str = 'manual') -> dict[str, Any]:
        position = self.storage.get_open_paper_position(symbol)
        if not position:
            raise ValueError(f'No existe una posición paper abierta para {symbol}.')
        direction = 1 if position['side'] == 'LONG' else -1
        gross = (float(price) - position['entry']) * position['quantity'] * direction
        fees = (position['entry'] + float(price)) * position['quantity'] * self.fee_rate
        net = gross - fees
        return self.storage.close_paper_position(position['id'], float(price), gross, fees, net, reason)
