"""Limitador de frecuencia compatible con código síncrono y asíncrono."""

import asyncio
import threading
import time


class RateLimiter:
    def __init__(self, calls_per_second: float):
        self._interval = 1.0 / calls_per_second if calls_per_second > 0 else 0.0
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()
        self._last = 0.0

    def wait(self) -> None:
        """Espera de forma bloqueante. Útil fuera de un bucle asíncrono."""
        if self._interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            delay = self._interval - (now - self._last)
            if delay > 0:
                time.sleep(delay)
            self._last = time.monotonic()

    async def wait_async(self) -> None:
        """Espera sin bloquear el hilo de la interfaz."""
        if self._interval <= 0:
            return
        async with self._async_lock:
            now = time.monotonic()
            delay = self._interval - (now - self._last)
            if delay > 0:
                await asyncio.sleep(delay)
            self._last = time.monotonic()
