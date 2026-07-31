from pathlib import Path
from depth_history import DepthHistoryStore
from futures_context import DerivativesContext, score_derivatives
from stress_recovery import FaultInjector, run_stress
from validation_campaign import CampaignStore
from order_reconciliation import OrderReconciler


def test_depth_history(tmp_path):
    s=DepthHistoryStore(tmp_path/'d.db')
    s.record('BTCUSDT',[['100','2']],[['101','3']])
    rows=s.recent('BTCUSDT'); assert len(rows)==1 and rows[0]['spread_bps']>0

def test_derivatives_scoring_is_bounded_and_explainable():
    r=score_derivatives(DerivativesContext(funding_rate=.001,order_book_imbalance=-.4,spread_bps=20))
    assert r['short']>r['long'] and r['warnings']

def test_stress_recovers():
    r=run_stress(lambda: True,attempts=30,retries=5,injector=FaultInjector(.35,(0,0),seed=7))
    assert r.successes+r.failures==30 and r.recoveries>=0

def test_campaign_compare(tmp_path):
    c=CampaignStore(tmp_path/'c.db')
    for src in ('backtest','paper','testnet'):
        c.record(src,'BTC/USDT','BUY',100,pnl=1,ok=True)
    out=c.compare('BTC/USDT'); assert len(out['sources'])==3 and out['signal_agreement_pct']==100.0

def test_reconciler_normalizes_partial_fill():
    x=OrderReconciler.normalize({'symbol':'BTCUSDT','clientOrderId':'x','status':'PARTIALLY_FILLED','executedQty':'2','cummulativeQuoteQty':'210'})
    assert x.avg_price==105 and x.status=='PARTIALLY_FILLED'
