import logging
from typing import Optional

logger = logging.getLogger(__name__)

class NotifierBase:
    def send(self, title: str, message: str):
        raise NotImplementedError

class LocalNotifier(NotifierBase):
    def send(self, title: str, message: str):
        logger.info("[LOCAL NOTIF] %s - %s", title, message)

class FCMNotifier(NotifierBase):
    def __init__(self, fcm_sender: Optional[object] = None):
        self.fcm_sender = fcm_sender

    def send(self, title: str, message: str):
        logger.info("[FCM NOTIF] %s - %s", title, message)