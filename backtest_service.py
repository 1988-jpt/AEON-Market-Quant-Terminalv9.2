"""Servicio de backtesting con paginación histórica, caché y multi-timeframe."""
from __future__ import annotations
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, Optional
import pandas as pd
from backtesting_engine import BacktestConfig, BacktestEngine, BacktestResult
from binance_client import BinanceClient
from data_analysis import ohlcv_to_df
from walk_forward import WalkForwardOptimizer
from market_cache import HistoricalCache

HIGHER={'1m':'5m','3m':'15m','5m':'15m','15m':'1h','30m':'4h','1h':'4h','2h':'8h','4h':'1d','6h':'1d','8h':'1d','12h':'3d','1d':'1w','3d':'1w'}
@dataclass
class BacktestServiceResult:
    symbol:str; timeframe:str; result:BacktestResult; optimization:Optional[Dict[str,Any]]=None; rows:int=0; higher_timeframe:Optional[str]=None; period_start:str=''; period_end:str=''

class BacktestService:
    def __init__(self,cache_dir:Optional[str]=None):
        self.cache_dir=Path(cache_dir) if cache_dir else None
        self.cache=HistoricalCache(str(self.cache_dir) if self.cache_dir else None)
    async def run(self,symbol:str,timeframe:str,limit:int=5000,optimize:bool=False,config:Optional[BacktestConfig]=None,since=None,until=None,use_higher_timeframe:bool=True)->BacktestServiceResult:
        cfg=replace(config or BacktestConfig(),timeframe=timeframe); client=BinanceClient()
        try:
            key={'symbol':symbol.upper(),'timeframe':timeframe,'since':str(since),'until':str(until),'limit':int(limit)}
            df=self.cache.get(key,dated=bool(until))
            if df is None:
                raw=await client.fetch_ohlcv_history(symbol,timeframe,since,until,max_bars=max(300,int(limit)))
                df=ohlcv_to_df(raw); self.cache.put(key,df)
            higher_tf=HIGHER.get(timeframe) if use_higher_timeframe else None; higher_df=None
            if higher_tf:
                hkey={'symbol':symbol.upper(),'timeframe':higher_tf,'since':str(df.index[0]),'until':str(df.index[-1]),'limit':int(limit)}
                higher_df=self.cache.get(hkey,dated=bool(until))
                if higher_df is None:
                    higher_raw=await client.fetch_ohlcv_history(symbol,higher_tf,since=df.index[0].to_pydatetime(),until=df.index[-1].to_pydatetime(),max_bars=max(300,int(limit)))
                    higher_df=ohlcv_to_df(higher_raw); self.cache.put(hkey,higher_df)
            engine=BacktestEngine()
            if optimize:
                opt=WalkForwardOptimizer(engine).optimize(df,cfg,higher_df); result=opt['test_result']
                return BacktestServiceResult(symbol,timeframe,result,opt,len(df),higher_tf,str(df.index[0]),str(df.index[-1]))
            result=engine.run(df,cfg,higher_df)
            return BacktestServiceResult(symbol,timeframe,result,None,len(df),higher_tf,str(df.index[0]),str(df.index[-1]))
        finally: await client.close()
