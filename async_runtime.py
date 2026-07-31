"""Bucle asyncio persistente para ejecutar servicios asíncronos desde Kivy.

Evita crear un bucle nuevo con ``asyncio.run`` en cada pulsación. Esto es
importante porque clientes HTTP, locks y semáforos asíncronos no deben moverse
entre bucles diferentes.
"""
from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future
from typing import Coroutine, Any


class AsyncRuntime:
    """Ejecuta corutinas en un único hilo/bucle durante toda la aplicación."""

    def __init__(self, name: str = "aeon-async-runtime") -> None:
        self._loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._closed = False
        self._thread = threading.Thread(target=self._run, name=name, daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=5):
            raise RuntimeError("No se pudo iniciar el motor asíncrono.")

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        self._loop.run_forever()
        pending = asyncio.all_tasks(self._loop)
        for task in pending:
            task.cancel()
        if pending:
            self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        self._loop.run_until_complete(self._loop.shutdown_asyncgens())
        self._loop.close()

    def submit(self, coroutine: Coroutine[Any, Any, Any]) -> Future:
        if self._closed or not self._thread.is_alive():
            coroutine.close()
            raise RuntimeError("El motor asíncrono ya está cerrado.")
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop)

    def shutdown(self, timeout: float = 8.0) -> None:
        if self._closed:
            return
        self._closed = True
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if threading.current_thread() is not self._thread:
            self._thread.join(timeout=timeout)
