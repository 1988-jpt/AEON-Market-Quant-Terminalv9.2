# AEON Market Quant Terminal V8 Professional

# Analizador profesional de mercado

Aplicación modular en Python y Kivy para analizar criptomonedas con datos públicos de Binance.

## Funciones

- Velas OHLCV y gráficos profesionales.
- EMA 9/21/50, SMA 200, RSI, MACD, Bandas de Bollinger, ATR, ADX, VWAP, OBV y estocástico.
- Patrones Doji, martillo, estrella fugaz, envolventes y estrellas de mañana/tarde.
- Soportes y resistencias por pivotes locales.
- Noticias automáticas por RSS y medidor de sentimiento.
- Estrategia multifactor con señal, puntuación y confianza explicable.
- Historial SQLite y modo interfaz/consola.

## Windows

```bash
python -m pip install -r requirements.txt
python main.py
```

Modo consola:

```bash
python main.py --once --symbol BTC/USDT --timeframe 1h
```

## Android

`buildozer.spec` es una base de compilación. Pandas, NumPy y Matplotlib pueden requerir una versión de python-for-android con recetas compatibles. La aplicación no ejecuta órdenes y no garantiza resultados futuros.


## Modo sofisticado en tiempo real

La pestaña **Gráfico** ahora utiliza un motor nativo de Kivy, preparado para escritorio y Android:

- Velas japonesas actualizadas mediante WebSocket público de Binance.
- Reconexión automática con espera progresiva.
- Zoom con la rueda del ratón y desplazamiento arrastrando.
- Cursor de inspección, EMA 9/21/50 y soportes/resistencias.
- Recalculo en vivo de RSI, MACD, ADX, ATR y VWAP.
- Nuevo análisis completo cuando se cierra cada vela.
- Diseño adaptable: cinco columnas en escritorio y dos columnas en pantallas estrechas.

Primero pulsa **ANALIZAR** para cargar el historial y después **TIEMPO REAL**. Para detener el flujo, pulsa **DETENER TIEMPO REAL**.

## Motor de precisión sin IA

La estrategia incluye filtros de régimen, confirmación de temporalidad superior, volumen relativo, OBV, eficiencia de tendencia, divergencias RSI y gestión de riesgo por ATR. Las señales se vuelven más selectivas: un mayor número de resultados `HOLD` es intencional para evitar operaciones con baja calidad. Ningún filtro garantiza ganancias; el porcentaje real debe medirse mediante backtesting.

## Motor de backtesting y validación

La pestaña **Backtesting** simula la estrategia sin IA, usando solo información disponible en cada vela. La entrada ocurre en la apertura siguiente a la señal e incluye comisión, deslizamiento, stop-loss, take-profit, tamaño de posición por riesgo y salida por tiempo.

La opción **Optimizar walk-forward** selecciona parámetros en un tramo de entrenamiento y evalúa la configuración elegida en datos posteriores no utilizados durante la selección. Esto reduce, pero no elimina, el riesgo de sobreajuste.

Métricas incluidas: retorno neto, porcentaje de aciertos, Profit Factor, expectativa, drawdown máximo, Sharpe aproximado, Sortino aproximado, factor de recuperación y duración media. Los resultados se exportan a JSON, CSV y PNG dentro de la carpeta de datos de la aplicación.

## Calidad v2: validación y backtesting reforzados

Esta versión añade descarga histórica paginada, confirmación de temporalidad superior durante el backtest, curva de capital mark-to-market, ejecución conservadora ante gaps, costes configurables, Sharpe/Sortino anualizados según temporalidad y walk-forward con múltiples ventanas.

Para un estudio serio se recomiendan al menos 5.000–20.000 velas, varias criptomonedas y un mínimo de 30 operaciones fuera de muestra. Los resultados históricos no garantizan resultados futuros.


## Rendimiento pre-APK
Esta versión incorpora precálculo causal de indicadores, caché histórica, descargas concurrentes, imports diferidos y redibujado limitado. Consulta `OPTIMIZACIONES_PRE_APK.md`.

## Versión 3.0: interfaz AΞON

La versión V3 añade un dashboard futurista propio, escáner multi-activo, perfiles persistentes, explicación estructurada de señales y diagnóstico del sistema. Consulta `MEJORAS_V3_FUTURISTA.md` para conocer los cambios.


## Versión 4.0

- Backend Binance REST público predeterminado, sin claves y sin CCXT obligatorio.
- Paper trading local y persistente; nunca envía órdenes reales.
- Salidas parciales, break-even, trailing ATR y límites de pérdida en backtesting.
- Monte Carlo y calibración empírica de la calidad técnica.
- Esquema SQLite V4 y validación estricta de velas OHLCV.

Para usar CCXT opcionalmente en escritorio:

```powershell
python -m pip install ccxt
$env:BINANCE_BACKEND="ccxt"
python main.py
```


## V5: Android y producción segura

- Android usa NumPy sin Pandas para análisis en vivo.
- `python v5_cli.py depth BTC/USDT` consulta profundidad.
- `python v5_cli.py futures BTCUSDT` consulta mark price, funding e interés abierto.
- `liquidation_stream.py` procesa liquidaciones públicas en vivo.
- `execution_engine.py` está aislado, usa Spot Testnet por defecto y no se conecta desde la interfaz.
- Las pruebas visuales requieren Kivy y un contexto OpenGL; se omiten automáticamente en entornos sin pantalla.

## V6 Preproducción

Consulte `V6_PREPRODUCCION.md` para campañas prolongadas, comparación backtest/paper/testnet, servicio Android, profundidad histórica, derivados, reconciliación y estrés.
