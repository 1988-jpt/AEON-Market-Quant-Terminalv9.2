import numpy as np
import pandas as pd
from dataclasses import replace
from backtesting_engine import BacktestConfig,BacktestEngine
from walk_forward import WalkForwardOptimizer

class ScriptedStrategy:
    def __init__(self,signal='BUY'): self.signal=signal; self.higher_seen=False
    def decide(self,data,sentiment,higher=None):
        self.higher_seen=self.higher_seen or higher is not None
        price=float(data.close.iloc[-1])
        return {'signal':self.signal,'confidence':90,'score':5,'atr':1,'trade_plan':{'stop_loss':price-2 if self.signal=='BUY' else price+2},'market_regime':{'regime':'tendencia'}}

def data(n=280,trend=.05):
    close=100+np.arange(n)*trend; idx=pd.date_range('2025-01-01',periods=n,freq='h',tz='UTC')
    return pd.DataFrame({'open':close,'high':close+.8,'low':close-.8,'close':close+.2,'volume':100},index=idx)

def cfg(**kw): return replace(BacktestConfig(warmup_bars=20,min_confidence=60,min_abs_score=1,max_bars_in_trade=3,timeframe='1h'),**kw)

def test_reproducible_metrics_and_mark_to_market():
    a=BacktestEngine(ScriptedStrategy()).run(data(),cfg()); b=BacktestEngine(ScriptedStrategy()).run(data(),cfg())
    assert a.metrics==b.metrics and {'equity','cash_equity','unrealized_pnl'}<=set(a.equity_curve.columns)

def test_higher_timeframe_is_consumed():
    s=ScriptedStrategy(); BacktestEngine(s).run(data(),cfg(),data(80,.2)); assert s.higher_seen

def test_gap_stop_exits_at_open_not_stop():
    d=data(30); d.iloc[22,d.columns.get_loc('open')]=90; d.iloc[22,d.columns.get_loc('high')]=91; d.iloc[22,d.columns.get_loc('low')]=89; d.iloc[22,d.columns.get_loc('close')]=90
    r=BacktestEngine(ScriptedStrategy()).run(d,cfg(max_bars_in_trade=20)); assert any(t['exit_reason']=='gap_stop' for t in r.trades)

def test_timeframe_specific_annualization():
    r=BacktestEngine(ScriptedStrategy()).run(data(),cfg(timeframe='5m')); assert r.metrics['annualization_bars']==105120

def test_costs_reduce_result():
    e=BacktestEngine(ScriptedStrategy()); cheap=e.run(data(),cfg(fee_rate=0,slippage_rate=0,spread_rate=0)); costly=e.run(data(),cfg(fee_rate=.002,slippage_rate=.001,spread_rate=.001)); assert costly.metrics['final_capital']<cheap.metrics['final_capital']

def test_no_lookahead_entry_is_next_bar():
    r=BacktestEngine(ScriptedStrategy()).run(data(),cfg()); assert all(t['entry_time']>t['signal_time'] for t in r.trades)

def test_walk_forward_builds_multiple_windows():
    r=WalkForwardOptimizer(BacktestEngine(ScriptedStrategy())).optimize(data(500),cfg(),train_bars=180,test_bars=80,step_bars=80,confidence_values=(60,),score_values=(1,),risk_values=(.01,),min_trades=1)
    assert r['windows_count']>=3 and len(r['windows'])==r['windows_count']
