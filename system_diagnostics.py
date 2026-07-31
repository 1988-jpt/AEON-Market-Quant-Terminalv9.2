"""Diagnóstico no invasivo de conectividad, almacenamiento y entorno."""
from __future__ import annotations
import os, platform, sqlite3, time
from pathlib import Path
from urllib.request import urlopen

class SystemDiagnostics:
    def __init__(self, data_dir: str, db_path: str): self.data_dir=Path(data_dir); self.db_path=Path(db_path)
    def run(self) -> dict:
        result={'python': platform.python_version(), 'platform': platform.platform(), 'checks': {}}
        t=time.perf_counter()
        try:
            with urlopen('https://api.binance.com/api/v3/time', timeout=5) as r: ok=r.status==200
            result['checks']['binance']={'ok':ok,'latency_ms':round((time.perf_counter()-t)*1000)}
        except Exception as exc: result['checks']['binance']={'ok':False,'error':str(exc)}
        try:
            self.data_dir.mkdir(parents=True,exist_ok=True); p=self.data_dir/'._write_test'; p.write_text('ok'); p.unlink()
            result['checks']['storage']={'ok':True,'free_mb':round(os.statvfs(self.data_dir).f_bavail*os.statvfs(self.data_dir).f_frsize/1024/1024,1) if hasattr(os,'statvfs') else None}
        except Exception as exc: result['checks']['storage']={'ok':False,'error':str(exc)}
        try:
            with sqlite3.connect(self.db_path) as c: c.execute('PRAGMA quick_check').fetchone()
            result['checks']['database']={'ok':True}
        except Exception as exc: result['checks']['database']={'ok':False,'error':str(exc)}
        return result
