"""Datos públicos de futuros USD-M: funding, interés abierto y liquidaciones en vivo."""
from __future__ import annotations
import requests
from dataclasses import dataclass

BASE='https://fapi.binance.com'
@dataclass(frozen=True)
class FuturesSnapshot:
    symbol:str; mark_price:float; index_price:float; funding_rate:float; next_funding_ms:int; open_interest:float

class FuturesMarketClient:
    def __init__(self,timeout:float=10): self.timeout=timeout; self.session=requests.Session()
    def snapshot(self,symbol:str)->FuturesSnapshot:
        s=symbol.replace('/','').replace('-','').upper()
        p=self.session.get(BASE+'/fapi/v1/premiumIndex',params={'symbol':s},timeout=self.timeout); p.raise_for_status(); pj=p.json()
        o=self.session.get(BASE+'/fapi/v1/openInterest',params={'symbol':s},timeout=self.timeout); o.raise_for_status(); oj=o.json()
        return FuturesSnapshot(s,float(pj['markPrice']),float(pj['indexPrice']),float(pj['lastFundingRate']),int(pj['nextFundingTime']),float(oj['openInterest']))
    def funding_history(self,symbol:str,limit:int=100):
        s=symbol.replace('/','').replace('-','').upper(); r=self.session.get(BASE+'/fapi/v1/fundingRate',params={'symbol':s,'limit':max(1,min(limit,1000))},timeout=self.timeout); r.raise_for_status(); return r.json()
