"""Motor NumPy para Android: evita Pandas en análisis en vivo y gráficos."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
import numpy as np

@dataclass
class CandleSeries:
    rows: List[Dict[str, float]]
    def copy(self): return CandleSeries([dict(r) for r in self.rows])
    def __len__(self): return len(self.rows)
    @property
    def empty(self): return not self.rows
    def tail(self,n:int): return CandleSeries(self.rows[-n:])

@dataclass(frozen=True)
class MobileAnalysisResult:
    symbol:str; timeframe:str; price:float; timestamp_ms:int; decision:Dict[str,Any]
    dataframe:CandleSeries; news:list; sentiment:Dict[str,Any]; saved:bool

def _ema(values:np.ndarray, period:int)->np.ndarray:
    out=np.full(values.shape,np.nan,dtype=float)
    if len(values)<period:return out
    alpha=2/(period+1); out[period-1]=float(np.mean(values[:period]))
    for i in range(period,len(values)): out[i]=alpha*values[i]+(1-alpha)*out[i-1]
    return out

def _rsi(values:np.ndarray, period:int=14)->np.ndarray:
    out=np.full(values.shape,np.nan); d=np.diff(values,prepend=values[0]); gain=np.maximum(d,0); loss=np.maximum(-d,0)
    ag=_ema(gain,period); al=_ema(loss,period); rs=np.divide(ag,al,out=np.full_like(ag,np.nan),where=al>1e-12); out=100-(100/(1+rs)); out[(al<=1e-12)&(ag>0)]=100; return out

def _atr(h,l,c,period=14):
    prev=np.roll(c,1); prev[0]=c[0]; tr=np.maximum(h-l,np.maximum(np.abs(h-prev),np.abs(l-prev))); return _ema(tr,period)

def analyze_ohlcv(rows:Iterable[Iterable[float]], symbol:str, timeframe:str, sentiment_score:float=0.0)->MobileAnalysisResult:
    raw=list(rows)
    if len(raw)<220: raise ValueError(f'Datos insuficientes: {len(raw)} velas; se requieren al menos 220.')
    a=np.asarray(raw,dtype=float); ts=a[:,0].astype(np.int64); o,h,l,c,v=a[:,1],a[:,2],a[:,3],a[:,4],a[:,5]
    e9,e21,e50=_ema(c,9),_ema(c,21),_ema(c,50); rsi=_rsi(c); atr=_atr(h,l,c)
    macd=_ema(c,12)-_ema(c,26); signal=_ema(np.nan_to_num(macd,nan=0.0),9); hist=macd-signal
    vol_ma=_ema(v,20); vol_ratio=float(v[-1]/vol_ma[-1]) if np.isfinite(vol_ma[-1]) and vol_ma[-1]>0 else 0.0
    up=e9[-1]>e21[-1]>e50[-1]; down=e9[-1]<e21[-1]<e50[-1]
    long_score=(2.2 if up else 0)+(1.3 if hist[-1]>0 else 0)+(1 if 48<=rsi[-1]<=68 else 0)+(1 if vol_ratio>=1.15 else 0)+max(0,sentiment_score)*.5
    short_score=(2.2 if down else 0)+(1.3 if hist[-1]<0 else 0)+(1 if 32<=rsi[-1]<=52 else 0)+(1 if vol_ratio>=1.15 else 0)+max(0,-sentiment_score)*.5
    edge=long_score-short_score; sig='BUY' if long_score>=4 and edge>=1.2 else ('SELL' if short_score>=4 and edge<=-1.2 else 'HOLD')
    confidence=float(min(95,max(35,50+abs(edge)*7+max(long_score,short_score)*3)))
    regime='tendencia_alcista' if up else ('tendencia_bajista' if down else 'transicion')
    stop=float(c[-1]-(1.8*atr[-1])) if sig=='BUY' else float(c[-1]+(1.8*atr[-1])) if sig=='SELL' else None
    tp1=float(c[-1]+(2.7*atr[-1])) if sig=='BUY' else float(c[-1]-(2.7*atr[-1])) if sig=='SELL' else None
    tp2=float(c[-1]+(4.5*atr[-1])) if sig=='BUY' else float(c[-1]-(4.5*atr[-1])) if sig=='SELL' else None
    records=[]
    for i in range(len(raw)):
        records.append({'timestamp_ms':int(ts[i]),'open':float(o[i]),'high':float(h[i]),'low':float(l[i]),'close':float(c[i]),'volume':float(v[i]),'ema_9':float(e9[i]),'ema_21':float(e21[i]),'ema_50':float(e50[i])})
    decision={'signal':sig,'confidence':confidence,'score':float(edge),'long_score':float(long_score),'short_score':float(short_score),'rsi':float(rsi[-1]),'macd':float(macd[-1]),'adx':0.0,'atr':float(atr[-1]),'vwap':float(np.average(c,weights=np.maximum(v,1e-9))),'volume_ratio':vol_ratio,'efficiency_ratio':float(abs(c[-1]-c[-11])/max(np.sum(np.abs(np.diff(c[-11:]))),1e-9)),'market_regime':{'regime':regime},'higher_timeframe':{'bias':'no_disponible_android'},'supports':[float(np.min(l[-30:]))],'resistances':[float(np.max(h[-30:]))],'patterns':[],'warnings':['Motor móvil NumPy: backtesting avanzado se ejecuta en escritorio.'],'reason':'Análisis NumPy optimizado para Android.','trade_plan':{'entry':float(c[-1]),'stop_loss':stop,'take_profit_1':tp1,'take_profit_2':tp2}}
    return MobileAnalysisResult(symbol,timeframe,float(c[-1]),int(ts[-1]),decision,CandleSeries(records),[],{'score':sentiment_score,'label':'NEUTRAL'},False)
