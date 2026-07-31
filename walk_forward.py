"""Walk-forward real con múltiples ventanas temporales y validación agregada."""
from __future__ import annotations
from dataclasses import asdict, replace
from itertools import product
from statistics import median
from typing import Any, Dict, Iterable, List, Optional
import pandas as pd
from backtesting_engine import BacktestConfig, BacktestEngine

class WalkForwardOptimizer:
    def __init__(self,engine:Optional[BacktestEngine]=None): self.engine=engine or BacktestEngine()
    def optimize(self,data:pd.DataFrame,base:Optional[BacktestConfig]=None,higher_timeframe_data:Optional[pd.DataFrame]=None,
                 train_bars:Optional[int]=None,test_bars:Optional[int]=None,step_bars:Optional[int]=None,
                 confidence_values:Iterable[float]=(64,68,72),score_values:Iterable[float]=(1.8,2.2,2.6),risk_values:Iterable[float]=(.005,.01),min_trades:int=10)->Dict[str,Any]:
        cfg=base or BacktestConfig(); n=len(data)
        train_bars=train_bars or max(cfg.warmup_bars+150,int(n*.5)); test_bars=test_bars or max(80,int(n*.15)); step_bars=step_bars or test_bars
        if train_bars+test_bars>n: raise ValueError('No hay datos suficientes para múltiples ventanas walk-forward.')
        grid=list(product(confidence_values,score_values,risk_values)); windows=[]; start=0
        while start+train_bars+test_bars<=n:
            train=data.iloc[start:start+train_bars]; test=data.iloc[start+train_bars-cfg.warmup_bars:start+train_bars+test_bars]
            ht_train=ht_test=None
            if higher_timeframe_data is not None and len(higher_timeframe_data):
                ht_train=higher_timeframe_data.loc[higher_timeframe_data.index<=train.index[-1]]
                ht_test=higher_timeframe_data.loc[higher_timeframe_data.index<=test.index[-1]]
            candidates=[]
            for confidence,score,risk in grid:
                c=replace(cfg,min_confidence=float(confidence),min_abs_score=float(score),risk_per_trade=float(risk))
                r=self.engine.run(train,c,ht_train); m=r.metrics; pf=float(m['profit_factor']) if isinstance(m['profit_factor'],(int,float)) else 4.0
                objective=float(m['net_return_pct'])+min(pf,4)*2-float(m['max_drawdown_pct'])*1.5
                if int(m['total_trades'])<min_trades: objective-=30*(1-int(m['total_trades'])/max(1,min_trades))
                candidates.append((objective,c,m))
            candidates.sort(key=lambda x:x[0],reverse=True); _,best,train_metrics=candidates[0]
            test_result=self.engine.run(test,best,ht_test)
            windows.append({'window':len(windows)+1,'train_start':str(train.index[0]),'train_end':str(train.index[-1]),'test_start':str(test.index[cfg.warmup_bars]),'test_end':str(test.index[-1]),'best_config':asdict(best),'train_metrics':train_metrics,'test_metrics':test_result.metrics,'test_result':test_result})
            start+=step_bars
        if not windows: raise ValueError('No se pudo crear ninguna ventana walk-forward.')
        returns=[w['test_metrics']['net_return_pct'] for w in windows]; pfs=[float(w['test_metrics']['profit_factor']) if isinstance(w['test_metrics']['profit_factor'],(int,float)) else 4.0 for w in windows]
        positive=sum(r>0 for r in returns); robustness='alta' if positive/len(windows)>=.7 and median(returns)>0 else 'media' if positive/len(windows)>=.5 else 'baja'
        representative=max(windows,key=lambda w:w['test_metrics']['net_return_pct'])
        return {'windows_count':len(windows),'positive_windows':positive,'positive_windows_pct':round(positive/len(windows)*100,2),'median_test_return_pct':round(float(median(returns)),2),'median_test_profit_factor':round(float(median(pfs)),3),'robustness':robustness,'windows':[{k:v for k,v in w.items() if k!='test_result'} for w in windows],'best_config':representative['best_config'],'test_metrics':representative['test_metrics'],'test_result':representative['test_result'],'performance_degradation_pct_points':round(float(median([w['train_metrics']['net_return_pct']-w['test_metrics']['net_return_pct'] for w in windows])),2)}
