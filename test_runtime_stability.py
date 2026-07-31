import asyncio
import logging

from async_runtime import AsyncRuntime
from realtime_feed import BinanceRealtimeFeed


def test_async_runtime_reuses_one_loop():
    runtime = AsyncRuntime('test-runtime')

    async def loop_id():
        return id(asyncio.get_running_loop())

    try:
        first = runtime.submit(loop_id()).result(timeout=2)
        second = runtime.submit(loop_id()).result(timeout=2)
        assert first == second
    finally:
        runtime.shutdown()


def test_realtime_stop_before_connection_is_safe():
    async def scenario():
        async def tick(_item):
            return None

        feed = BinanceRealtimeFeed('BTC/USDT', '1h', tick)
        await feed.stop()
        assert feed._stop_event.is_set()

    asyncio.run(scenario())


def test_logging_does_not_add_second_console_for_kivy_handler(tmp_path, monkeypatch):
    import logging_config

    class FakeKivyHandler(logging.Handler):
        __module__ = 'kivy.logger'
        def emit(self, record):
            pass

    root = logging.getLogger()
    old_handlers = list(root.handlers)
    old_flag = getattr(root, '_market_analyzer_configured', False)
    try:
        root.handlers[:] = [FakeKivyHandler()]
        if hasattr(root, '_market_analyzer_configured'):
            delattr(root, '_market_analyzer_configured')
        logging_config.setup_logging(str(tmp_path / 'app.log'))
        console_handlers = [h for h in root.handlers if type(h) is logging.StreamHandler]
        assert console_handlers == []
    finally:
        for handler in root.handlers:
            if handler not in old_handlers:
                handler.close()
        root.handlers[:] = old_handlers
        root._market_analyzer_configured = old_flag
