"""Configuración validada y segura de la aplicación."""
from __future__ import annotations
import os
from pathlib import Path
def _load_local_env() -> None:
    """Carga .env sin depender de python-dotenv.

    En Android normalmente no existe un archivo .env; en escritorio este parser
    ligero conserva la compatibilidad con claves simples KEY=VALUE.
    """
    env_path = Path(__file__).resolve().with_name(".env")
    if not env_path.is_file():
        return
    try:
        for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key.replace("_", "").isalnum():
                os.environ.setdefault(key, value)
    except OSError:
        # La configuración predeterminada debe permitir que la app inicie aun
        # cuando el almacenamiento no esté disponible temporalmente.
        pass


_load_local_env()

VALID_TIMEFRAMES = ('1m','3m','5m','15m','30m','1h','2h','4h','6h','8h','12h','1d','3d','1w')
VALID_LOG_LEVELS = ('DEBUG','INFO','WARNING','ERROR','CRITICAL')

def _int(name: str, default: int, minimum: int, maximum: int) -> int:
    try: value = int(os.getenv(name, str(default)))
    except ValueError: value = default
    return max(minimum, min(value, maximum))

def _float(name: str, default: float, minimum: float, maximum: float) -> float:
    try: value = float(os.getenv(name, str(default)))
    except ValueError: value = default
    return max(minimum, min(value, maximum))

BINANCE_API_KEY = os.getenv('BINANCE_API_KEY','').strip() or None
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET','').strip() or None
OHLCV_TIMEFRAME = os.getenv('OHLCV_TIMEFRAME','1h').strip()
if OHLCV_TIMEFRAME not in VALID_TIMEFRAMES: OHLCV_TIMEFRAME = '1h'
OHLCV_LIMIT = _int('OHLCV_LIMIT', 500, 220, 100_000)
DB_PATH = str(Path(os.getenv('DB_PATH','app_data.db')).expanduser())
LOG_LEVEL = os.getenv('LOG_LEVEL','INFO').upper()
if LOG_LEVEL not in VALID_LOG_LEVELS: LOG_LEVEL = 'INFO'
BACKTEST_INITIAL_CAPITAL = _float('BACKTEST_INITIAL_CAPITAL', 10_000, 100, 100_000_000)
BACKTEST_RISK = _float('BACKTEST_RISK', .01, .001, .05)
BACKTEST_FEE = _float('BACKTEST_FEE', .001, 0, .02)
BACKTEST_SLIPPAGE = _float('BACKTEST_SLIPPAGE', .0003, 0, .02)

BINANCE_BACKEND = os.getenv('BINANCE_BACKEND','public_rest').strip().lower()
if BINANCE_BACKEND not in ('public_rest','ccxt'): BINANCE_BACKEND='public_rest'
