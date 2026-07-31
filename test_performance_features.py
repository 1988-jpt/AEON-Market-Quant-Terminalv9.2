import pandas as pd
import numpy as np
from pathlib import Path

from advanced_strategy import AdvancedStrategy
from market_cache import HistoricalCache
from technical_indicators import add_quality_indicators

def _frame(n=260):
    idx=pd.date_range("2025-01-01",periods=n,freq="h")
    close=np.linspace(100,130,n)+np.sin(np.arange(n)/7)
    return pd.DataFrame({
        "open":close-.1,"high":close+.5,"low":close-.5,
        "close":close,"volume":np.linspace(1000,1400,n)
    },index=idx)

def test_precomputed_indicators_keep_same_decision():
    raw=_frame()
    prepared=add_quality_indicators(raw)
    strategy=AdvancedStrategy()
    a=strategy.decide(raw)
    b=strategy.decide(prepared)
    for key in ("signal","score","confidence","rsi","adx"):
        assert a[key] == b[key]

def test_historical_cache_roundtrip(tmp_path: Path):
    cache=HistoricalCache(str(tmp_path))
    key={"symbol":"BTC/USDT","timeframe":"1h","limit":300}
    frame=_frame()
    assert cache.get(key) is None
    cache.put(key,frame)
    loaded=cache.get(key)
    pd.testing.assert_frame_equal(frame,loaded)
