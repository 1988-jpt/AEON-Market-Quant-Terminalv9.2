"""Detección de plataforma sin importar Kivy durante pruebas o modo consola."""
from __future__ import annotations
import os, sys


def is_android() -> bool:
    return bool(os.getenv('ANDROID_ARGUMENT')) or sys.platform == 'android'


def is_desktop() -> bool:
    return not is_android()
