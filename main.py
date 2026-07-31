"""Punto de entrada multiplataforma de AEON Market Quant Terminal."""
from __future__ import annotations

import asyncio
import logging
import os
import sys

from config import OHLCV_TIMEFRAME
from logging_config import setup_logging

logger = logging.getLogger(__name__)


def _is_android() -> bool:
    return bool(os.getenv("ANDROID_ARGUMENT")) or sys.platform == "android"


async def run_once(symbol: str, timeframe: str = OHLCV_TIMEFRAME):
    """Ejecuta un análisis único en escritorio/consola."""
    from analyzer_service import MarketAnalyzerService
    from notifier import LocalNotifier

    service = MarketAnalyzerService()
    try:
        result = await service.analyze(symbol=symbol, timeframe=timeframe)
        decision = result.decision
        LocalNotifier().send(
            f"Señal {result.symbol}",
            f"{decision['signal']} a {result.price:.4f} ({decision.get('reason')})",
        )
        return result
    finally:
        close = getattr(service, "close", None)
        if close is not None:
            value = close()
            if asyncio.iscoroutine(value):
                await value


def _desktop_args():
    import argparse

    parser = argparse.ArgumentParser(description="Analizador técnico de mercado")
    parser.add_argument("--once", action="store_true", help="Ejecuta un análisis sin interfaz")
    parser.add_argument("--symbol", default="BTC/USDT", help="Par, por ejemplo BTC/USDT")
    parser.add_argument("--timeframe", default=OHLCV_TIMEFRAME, help="Temporalidad, por ejemplo 1h")
    return parser.parse_args()


def main() -> None:
    # Android configura el log después de obtener App.user_data_dir. Intentar
    # escribir app.log antes de eso puede cerrar la APK en algunos dispositivos.
    if _is_android():
        try:
            from android_runtime_guard import install_exception_hook, write_crash_report
            install_exception_hook()
            from android_bootstrap_app import AndroidBootstrapApp
            AndroidBootstrapApp().run()
        except BaseException as exc:
            try:
                write_crash_report(exc)
            finally:
                raise
        return

    setup_logging("app.log")

    args = _desktop_args()
    if args.once:
        result = asyncio.run(run_once(args.symbol, args.timeframe))
        print(result.decision)
        return

    try:
        from mobile_app import MarketAnalyzerApp
    except ModuleNotFoundError as exc:
        if exc.name != "kivy":
            raise
        logger.warning("Kivy no está instalado; se ejecutará un análisis por consola.")
        asyncio.run(run_once(args.symbol, args.timeframe))
        return
    MarketAnalyzerApp().run()


if __name__ == "__main__":
    main()
