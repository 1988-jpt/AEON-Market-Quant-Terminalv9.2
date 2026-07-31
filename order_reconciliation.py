"""Reconciliación idempotente de órdenes Binance Spot/Testnet."""
from __future__ import annotations
import time, uuid
from dataclasses import dataclass

TERMINAL={'FILLED','CANCELED','REJECTED','EXPIRED','EXPIRED_IN_MATCH'}
@dataclass(frozen=True)
class ReconciledOrder:
    symbol:str; client_order_id:str; status:str; executed_qty:float; quote_qty:float; avg_price:float; raw:dict

class OrderReconciler:
    def __init__(self, engine, poll_seconds=1.0, timeout_seconds=30.0):
        self.engine=engine; self.poll=max(.1,float(poll_seconds)); self.timeout=max(1,float(timeout_seconds))
    @staticmethod
    def client_id(prefix='AEON'):
        return f'{prefix}-{int(time.time())}-{uuid.uuid4().hex[:10]}'[:36]
    @staticmethod
    def normalize(raw):
        qty=float(raw.get('executedQty',0) or 0); quote=float(raw.get('cummulativeQuoteQty',0) or 0)
        avg=quote/qty if qty>0 else 0.0
        return ReconciledOrder(str(raw.get('symbol','')),str(raw.get('clientOrderId') or raw.get('origClientOrderId','')),str(raw.get('status','UNKNOWN')),qty,quote,avg,raw)
    def wait_terminal(self,symbol,client_order_id):
        deadline=time.monotonic()+self.timeout; last=None
        while time.monotonic()<deadline:
            last=self.engine.get_order(symbol,client_order_id)
            obj=self.normalize(last)
            if obj.status in TERMINAL:return obj
            time.sleep(self.poll)
        raise TimeoutError(f'La orden {client_order_id} no llegó a estado terminal. Último estado: {last}')
    def reconcile_open(self,symbol):
        return [self.normalize(x) for x in self.engine.open_orders(symbol)]
