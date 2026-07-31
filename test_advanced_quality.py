import numpy as np
import pandas as pd
from advanced_strategy import AdvancedStrategy


def make_df(direction=1.0, n=260, noisy=False):
    rng = np.random.default_rng(7)
    base = 100 + direction * np.linspace(0, 35, n)
    noise = rng.normal(0, 0.3 if not noisy else 2.0, n)
    close = base + noise
    idx = pd.date_range('2025-01-01', periods=n, freq='h')
    open_ = np.r_[close[0], close[:-1]]
    high = np.maximum(open_, close) + 0.8
    low = np.minimum(open_, close) - 0.8
    volume = np.linspace(1000, 1800, n)
    return pd.DataFrame({'open': open_, 'high': high, 'low': low, 'close': close, 'volume': volume}, index=idx)


def test_strategy_returns_quality_metadata():
    result = AdvancedStrategy().decide(make_df(1), 0.2, make_df(1))
    assert result['signal'] in {'BUY', 'SELL', 'HOLD'}
    assert 'market_regime' in result
    assert 'trade_plan' in result
    assert 0 <= result['confidence'] <= 92


def test_conflicting_higher_timeframe_blocks_weak_entry():
    result = AdvancedStrategy().decide(make_df(1), 0.0, make_df(-1))
    assert result['signal'] != 'BUY'
