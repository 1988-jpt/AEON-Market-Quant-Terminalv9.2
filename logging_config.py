"""Configuración de logging tolerante a fallos para escritorio y Android."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from config import LOG_LEVEL


def setup_logging(log_path: Optional[str] = None, *, force: bool = False) -> None:
    """Configura logging sin impedir el arranque si el almacenamiento falla.

    En Android el archivo debe estar dentro de ``App.user_data_dir``. Si no es
    posible crear el archivo, la aplicación continúa usando únicamente consola.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    if getattr(root, "_aeon_logging_configured", False) and not force:
        return

    if force:
        for handler in list(root.handlers):
            if getattr(handler, "_aeon_handler", False):
                try:
                    handler.close()
                finally:
                    root.removeHandler(handler)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    if log_path:
        try:
            target = Path(log_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                target,
                maxBytes=2_000_000,
                backupCount=2,
                encoding="utf-8",
                delay=True,
            )
            file_handler.setFormatter(formatter)
            file_handler._aeon_handler = True
            root.addHandler(file_handler)
        except Exception as exc:
            # Nunca se permite que un fallo del log cierre la APK.
            try:
                sys.stderr.write(f"AEON: no se pudo activar el log de archivo: {exc}\n")
            except Exception:
                pass

    has_console = any(
        isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, RotatingFileHandler)
        for handler in root.handlers
    )
    has_kivy_console = any(
        handler.__class__.__module__.startswith("kivy") for handler in root.handlers
    )
    if not has_console and not has_kivy_console:
        try:
            console = logging.StreamHandler(sys.stdout)
            console.setFormatter(formatter)
            console._aeon_handler = True
            root.addHandler(console)
        except Exception:
            pass

    root._aeon_logging_configured = True
