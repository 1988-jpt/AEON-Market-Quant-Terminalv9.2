"""Protecciones de arranque y reporte de errores para Android."""
from __future__ import annotations

import logging
import os
import sys
import traceback
import threading
import faulthandler
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _fallback_dirs(preferred: Optional[Path] = None):
    seen = set()
    for candidate in (
        preferred,
        Path(os.environ.get("HOME", "")) if os.environ.get("HOME") else None,
        Path.cwd(),
    ):
        if candidate is None:
            continue
        try:
            candidate = candidate.expanduser().resolve()
        except Exception:
            continue
        if str(candidate) not in seen:
            seen.add(str(candidate))
            yield candidate


def write_crash_report(exc: BaseException, data_dir: Optional[Path] = None, *, phase: str = "runtime") -> Optional[Path]:
    """Guarda un informe de excepción en el primer directorio escribible."""
    report = (
        f"AEON Android crash report\n"
        f"Phase: {phase}\n"
        f"UTC: {datetime.now(timezone.utc).isoformat()}\n"
        f"Python: {sys.version}\n"
        f"Platform: {sys.platform}\n\n"
        + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    )
    for base in _fallback_dirs(data_dir):
        try:
            base.mkdir(parents=True, exist_ok=True)
            path = base / "aeon_startup_crash.log"
            path.write_text(report, encoding="utf-8")
            return path
        except Exception:
            continue
    return None


def install_exception_hook(data_dir: Optional[Path] = None) -> None:
    """Instala un hook que registra excepciones no controladas."""
    previous = sys.excepthook

    def hook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            previous(exc_type, exc, tb)
            return
        try:
            write_crash_report(exc, data_dir)
            logger.critical("Excepción no controlada", exc_info=(exc_type, exc, tb))
        except Exception:
            pass
        previous(exc_type, exc, tb)

    sys.excepthook = hook


def install_thread_exception_hook(data_dir: Optional[Path] = None) -> None:
    """Registra fallos no controlados producidos por hilos secundarios."""
    if not hasattr(threading, "excepthook"):
        return
    previous = threading.excepthook

    def hook(args):
        try:
            write_crash_report(args.exc_value, data_dir, phase=f"thread:{args.thread.name}")
            logger.critical(
                "Excepción no controlada en hilo %s",
                args.thread.name,
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )
        except Exception:
            pass
        previous(args)

    threading.excepthook = hook


def enable_fault_log(data_dir: Path) -> Optional[Path]:
    """Activa faulthandler para fallos nativos cuando la plataforma lo permite."""
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        path = data_dir / "aeon_native_fault.log"
        stream = path.open("a", encoding="utf-8")
        faulthandler.enable(file=stream, all_threads=True)
        # Mantener referencia viva durante toda la ejecución.
        enable_fault_log._stream = stream
        return path
    except Exception:
        return None
