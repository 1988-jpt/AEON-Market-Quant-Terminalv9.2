import sqlite3
import numpy as np
import pandas as pd

from binance_rest_client import BinancePublicRestClient
from confidence_calibration import calibrate_confidence
from monte_carlo import run_monte_carlo
from paper_trading import PaperTradingEngine
from storage import Storage


def test_public_client_validates_without_ccxt():
    assert BinancePublicRestClient._validate('btc-usdt', '1h') == 'BTC/USDT'


def test_monte_carlo_is_reproducible():
    trades = [{'net_pnl': x} for x in (10, -4, 8, -2, 5)]
    a = run_monte_carlo(trades, 1000, simulations=200, seed=7)
    b = run_monte_carlo(trades, 1000, simulations=200, seed=7)
    assert a == b and a['available']


def test_confidence_calibration_buckets():
    trades = [{'confidence': 72, 'net_pnl': 5, 'return_pct': 1},
              {'confidence': 73, 'net_pnl': -2, 'return_pct': -.4}]
    result = calibrate_confidence(trades, minimum_samples=2)
    assert result['calibrated'] and result['reliable_buckets'][0]['win_rate_pct'] == 50


def test_paper_trading_persists_and_closes(tmp_path):
    storage = Storage(str(tmp_path / 'paper.db'))
    engine = PaperTradingEngine(storage, initial_balance=1000, fee_rate=0)
    decision = {'signal': 'BUY', 'confidence': 80,
                'trade_plan': {'stop_loss': 90, 'take_profit_2': 120}}
    assert engine.open_from_decision('BTC/USDT', 100, decision)
    closed = engine.close('BTC/USDT', 110)
    assert closed['net_pnl'] > 0
    assert engine.account()['balance'] > 1000


def test_storage_paper_schema_is_unique(tmp_path):
    storage = Storage(str(tmp_path / 'schema.db'))
    engine = PaperTradingEngine(storage)
    decision = {'signal': 'BUY', 'confidence': 80,
                'trade_plan': {'stop_loss': 90, 'take_profit_2': 120}}
    engine.open_from_decision('BTC/USDT', 100, decision)
    try:
        engine.open_from_decision('BTC/USDT', 100, decision)
    except ValueError:
        pass
    else:
        raise AssertionError('Debió impedir una segunda posición abierta del mismo símbolo')
