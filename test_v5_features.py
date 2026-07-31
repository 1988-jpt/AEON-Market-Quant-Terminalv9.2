import asyncio
from decimal import Decimal
from mobile_market_core import analyze_ohlcv,CandleSeries
from order_book import analyze_order_book
from native_notifications import NativeNotifier
from candle_recovery import CandleRecoveryManager
from execution_engine import SafeSpotExecutionEngine,ExecutionPolicy

def synthetic(n=240):
    rows=[]
    for i in range(n):
        p=100+i*.05; rows.append([i*3600000,p,p+1,p-1,p+.2,100+i%7])
    return rows

def test_numpy_android_engine_without_pandas():
    r=analyze_ohlcv(synthetic(),'BTC/USDT','1h'); assert len(r.dataframe)==240; assert r.decision['signal'] in {'BUY','SELL','HOLD'}

def test_order_book_metrics():
    m=analyze_order_book([['100','2'],['99','3']],[['101','1'],['102','2']]); assert m.spread==1; assert -1<=m.imbalance<=1

def test_notification_dedup():
    n=NativeNotifier(999); assert n.send('a','b','x'); assert not n.send('a','b','x')

def test_safe_execution_rejects_without_confirmation():
    e=SafeSpotExecutionEngine('k','s',ExecutionPolicy(max_notional_usdt=Decimal('10')))
    try:e.validate_order('BTCUSDT','BUY','0.01','1000','bad')
    except PermissionError:pass
    else:raise AssertionError

def test_recovery_gap():
    class C:
        async def fetch_ohlcv_range(self,*a,**k): return [[3600000,1,2,.5,1.5,3],[7200000,1,2,.5,1.5,3]]
    rows=asyncio.run(CandleRecoveryManager(C()).recover('BTC/USDT','1h',0,10800000)); assert len(rows)==2
from liquidation_stream import parse_liquidation

def test_liquidation_parser():
    e=parse_liquidation({'E':123,'o':{'s':'BTCUSDT','S':'SELL','p':'50000','q':'0.2','ap':'49990','X':'FILLED','T':122}})
    assert e.symbol=='BTCUSDT' and e.quantity==.2
