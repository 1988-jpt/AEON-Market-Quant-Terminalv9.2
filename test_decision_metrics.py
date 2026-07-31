from decision_metrics import derive_decision_metrics


def test_metrics_are_bounded_and_explainable():
    d = {
        'signal': 'BUY', 'long_score': 8, 'short_score': 3,
        'confidence': 82, 'atr': 2, 'warnings': ['x'],
        'market_regime': {'volatility': 'normal'},
    }
    m = derive_decision_metrics(d, 100)
    assert 0 <= m['buy_probability'] <= 100
    assert round(m['buy_probability'] + m['sell_probability'], 1) == 100.0
    assert m['risk_level'] in {'BAJO', 'MEDIO', 'ALTO', 'MUY ALTO'}
    assert 'no es una probabilidad' in m['label']
