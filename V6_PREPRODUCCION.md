# AEON V6 — Preproducción y evidencia operativa

Esta versión añade infraestructura para campañas de 30–90 días, paper multi-activo, comparación backtest/paper/testnet, snapshots históricos de profundidad, contexto de funding/liquidaciones, reconciliación de órdenes, servicio Android y pruebas de estrés.

## Límites honestos

- Una campaña de 30–90 días no puede completarse instantáneamente: el software queda preparado para recolectar la evidencia.
- La APK debe compilarse con Buildozer y probarse físicamente en varios dispositivos.
- Mainnet continúa bloqueado por defecto. La reconciliación se prueba primero en Binance Spot Testnet.

## Comandos

```powershell
python v5_cli.py stress --attempts 1000 --failure-rate 0.25
python v5_cli.py compare BTC/USDT
python v5_cli.py depth BTC/USDT
python v5_cli.py futures BTCUSDT
pytest -q
```

## Criterio de avance

No habilitar capital real hasta tener simultáneamente: campaña prolongada aprobada, paper multi-activo estable, Testnet reconciliado, ausencia de órdenes duplicadas, APK estable y pruebas de recuperación aprobadas.
