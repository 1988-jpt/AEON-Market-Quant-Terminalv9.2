# Motor de backtesting avanzado sin IA

## Principios
- Sin look-ahead: señal al cierre y entrada en la apertura siguiente.
- Una posición a la vez para evitar capital duplicado.
- Comisiones y deslizamiento configurables.
- Tamaño de posición basado en porcentaje de riesgo.
- Resolución intrabar conservadora: si stop y objetivo se tocan en la misma vela, se asume primero el stop.
- Salida por tiempo para evitar posiciones eternas.
- Validación walk-forward con tramo de entrenamiento y tramo fuera de muestra.

## Archivos
- `backtesting_engine.py`: simulador y métricas.
- `walk_forward.py`: optimización y evaluación fuera de muestra.
- `backtest_service.py`: descarga de datos y coordinación.
- `backtest_report.py`: exportación de resultados.
- `test_backtesting_engine.py`: pruebas de reproducibilidad.

## Interpretación
El porcentaje de aciertos no debe evaluarse solo. Un sistema puede ser rentable con menos del 50% si la ganancia media supera claramente la pérdida media. Revisar conjuntamente Profit Factor, expectativa, drawdown, retorno neto y cantidad de operaciones.
