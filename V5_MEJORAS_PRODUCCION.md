# AΞON V5 — Producción segura y Android ligero

- Android usa `mobile_market_core.py` con NumPy y no importa Pandas.
- Backtesting avanzado permanece en escritorio para conservar precisión y evitar consumo excesivo en móvil.
- Pruebas visuales Kivy con FBO y pytest.
- Notificaciones nativas mediante Plyer con deduplicación.
- Recuperación REST de velas perdidas después de suspensión o cortes.
- Diario persistente para paper trading prolongado.
- Validación masiva multi-activo y multi-timeframe.
- Profundidad de mercado, spread e imbalance.
- Funding e interés abierto de futuros USD-M.
- Ejecución Spot aislada: testnet por defecto, lista blanca, máximo notional, límite de pérdida y frase de confirmación.

La ejecución real no se activa desde la interfaz y no debe habilitarse antes de completar pruebas prolongadas en testnet.
