"""Pruebas de estrés deterministas para red, datos, almacenamiento y reinicios."""
from __future__ import annotations
import random,time
from dataclasses import dataclass

@dataclass
class StressReport:
    attempts:int; successes:int; failures:int; recoveries:int; max_consecutive_failures:int; elapsed_seconds:float

class FaultInjector:
    def __init__(self, failure_rate=.2, latency_ms=(0,50), seed=42):
        self.rate=max(0,min(1,float(failure_rate))); self.latency=latency_ms; self.rng=random.Random(seed)
    def call(self,fn,*args,**kwargs):
        low,high=self.latency; time.sleep(self.rng.uniform(low,high)/1000)
        if self.rng.random()<self.rate: raise ConnectionError('Fallo de red inyectado')
        return fn(*args,**kwargs)

def run_stress(operation,attempts=100,retries=3,injector=None):
    injector=injector or FaultInjector(); ok=fail=recoveries=consecutive=max_consecutive=0; start=time.monotonic()
    for _ in range(max(1,int(attempts))):
        completed=False
        for retry in range(max(0,int(retries))+1):
            try:
                injector.call(operation); ok+=1; recoveries+=int(retry>0); completed=True; consecutive=0; break
            except Exception:
                if retry>=retries: fail+=1; consecutive+=1; max_consecutive=max(max_consecutive,consecutive)
        if not completed: continue
    return StressReport(attempts,ok,fail,recoveries,max_consecutive,round(time.monotonic()-start,3))
