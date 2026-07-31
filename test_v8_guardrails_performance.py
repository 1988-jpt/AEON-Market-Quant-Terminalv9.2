from decimal import Decimal
import pytest
from operational_guardrails import GuardrailPolicy, OperationalGuardrails
from performance_cache import TTLCache


def test_guardrails_block_duplicate_and_notional():
    now = [100.0]
    policy = GuardrailPolicy(max_notional_usdt=Decimal('100'), allowed_symbols=('BTCUSDT',))
    guard = OperationalGuardrails(policy, clock=lambda: now[0])
    result = guard.validate(symbol='BTC/USDT', side='buy', quantity='0.001', reference_price='50000', request_id='abc')
    assert result[0] == 'BTCUSDT'
    with pytest.raises(PermissionError):
        guard.validate(symbol='BTCUSDT', side='BUY', quantity='0.001', reference_price='50000', request_id='abc')
    with pytest.raises(PermissionError):
        guard.validate(symbol='BTCUSDT', side='BUY', quantity='1', reference_price='50000')


def test_guardrails_daily_loss():
    guard = OperationalGuardrails(GuardrailPolicy(max_daily_loss_usdt=Decimal('5')))
    guard.register_realized_pnl('-5')
    with pytest.raises(PermissionError):
        guard.validate(symbol='BTCUSDT', side='BUY', quantity='0.0001', reference_price='50000')


def test_ttl_cache_expiry_and_lru():
    now = [0.0]
    cache = TTLCache(ttl_seconds=10, max_items=2, clock=lambda: now[0])
    cache.set('a', 1)
    assert cache.get('a') == 1
    now[0] = 11
    assert cache.get('a') is None
    cache.set('a', 1); cache.set('b', 2); cache.set('c', 3)
    assert cache.get('a') is None
    assert cache.get('c') == 3
