from pathlib import Path
from profile_manager import ProfileManager, AnalysisProfile
from signal_explainer import explain
from system_diagnostics import SystemDiagnostics

def test_profile_roundtrip(tmp_path):
    manager=ProfileManager(str(tmp_path/'profiles.json'))
    manager.save(AnalysisProfile('Prueba','15m',800,73,0.8,'spot'))
    loaded=manager.load()['Prueba']
    assert loaded.timeframe=='15m' and loaded.bars==800 and loaded.min_confidence==73

def test_signal_explanation_contains_risks_and_strengths():
    d={'signal':'BUY','confidence':80,'reason':'Tendencia confirmada','adx':30,'volume_ratio':1.4,
       'market_regime':{'regime':'tendencia_alcista'},'higher_timeframe':{'bias':'alcista','strength':'fuerte'},
       'warnings':['RSI elevado'],'patterns':['Martillo'],'trade_plan':{}}
    out=explain(d)
    assert out['positives'] and out['risks'] and out['summary']=='Tendencia confirmada'

def test_diagnostics_storage_and_database(tmp_path):
    db=tmp_path/'app.db'
    import sqlite3
    sqlite3.connect(db).close()
    result=SystemDiagnostics(str(tmp_path),str(db)).run()
    assert result['checks']['storage']['ok'] is True
    assert result['checks']['database']['ok'] is True
