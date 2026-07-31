"""Reportes reproducibles de backtesting."""
from __future__ import annotations
import hashlib,json,logging
from datetime import datetime,timezone
from pathlib import Path
from typing import Dict,Optional
import pandas as pd
logger=logging.getLogger(__name__)

def export_backtest(result,output_dir:str,prefix:str='backtest',metadata:Optional[dict]=None)->Dict[str,str]:
    d=Path(output_dir); d.mkdir(parents=True,exist_ok=True); stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    fingerprint=hashlib.sha256(json.dumps(result.config,sort_keys=True).encode()).hexdigest()[:10]; base=f'{prefix}_{stamp}_{fingerprint}'
    mp,tp,ep,cp=(d/f'{base}_metrics.json',d/f'{base}_trades.csv',d/f'{base}_equity.csv',d/f'{base}_equity.png')
    payload={'generated_at_utc':stamp,'strategy_version':'rules-v2','config_hash':fingerprint,'metadata':metadata or {},'config':result.config,'metrics':result.metrics}
    mp.write_text(json.dumps(payload,indent=2,ensure_ascii=False,default=str),encoding='utf-8'); pd.DataFrame(result.trades).to_csv(tp,index=False); result.equity_curve.to_csv(ep)
    chart=''
    try:
        import matplotlib.pyplot as plt
        fig=plt.figure(figsize=(10,5)); ax=fig.add_subplot(111); ax.plot(result.equity_curve.index,result.equity_curve['equity']); ax.set_title('Curva de capital mark-to-market'); ax.set_xlabel('Fecha'); ax.set_ylabel('Capital'); ax.grid(True,alpha=.25); fig.tight_layout(); fig.savefig(cp,dpi=140); plt.close(fig); chart=str(cp)
    except Exception as exc: logger.exception('No se pudo exportar el gráfico: %s',exc)
    return {'metrics':str(mp),'trades':str(tp),'equity':str(ep),'chart':chart}
