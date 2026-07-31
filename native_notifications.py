"""Notificaciones nativas con deduplicación y degradación segura."""
from __future__ import annotations
import logging,time
logger=logging.getLogger(__name__)
class NativeNotifier:
    def __init__(self,cooldown_seconds:int=300): self.cooldown=max(0,cooldown_seconds); self._last={}
    def send(self,title:str,message:str,key:str='default')->bool:
        now=time.time()
        if now-self._last.get(key,0)<self.cooldown:return False
        try:
            from plyer import notification
            notification.notify(title=title,message=message,app_name='AΞON Market Quant Terminal',timeout=10)
        except Exception:
            logger.info('[NOTIFICACIÓN] %s - %s',title,message)
        self._last[key]=now; return True
