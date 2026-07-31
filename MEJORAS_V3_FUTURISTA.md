# AΞON Market Quant Terminal V3

## Objetivo

Esta versión eleva la experiencia visual y operativa sin alterar el motor técnico existente. El diseño se inspira en terminales cuantitativos modernos, pero utiliza una identidad propia: fondo azul profundo, paneles con bordes cian, acentos púrpura, tarjetas de métricas y navegación lateral.

## Mejoras principales

- Interfaz completamente reorganizada con barra lateral y pantallas especializadas.
- Dashboard con señal, precio, calidad técnica, sentimiento, gráfico y contexto.
- Explicación transparente con fortalezas, riesgos y plan orientativo.
- Escáner concurrente multi-activo para hasta 20 pares por ejecución.
- Perfiles Conservador, Moderado, Agresivo y Swing, además de perfiles personalizados.
- Diagnóstico de Binance, latencia, base de datos y almacenamiento.
- Laboratorio de backtesting y walk-forward integrado en la nueva interfaz.
- Vista separada para noticias, historial, mercado y configuración.
- Diseño adaptable: barra lateral compacta en ventanas pequeñas.
- Sin ejecución automática de órdenes ni uso de claves privadas.

## Rendimiento y seguridad

Los cálculos pesados permanecen en hilos de trabajo y las modificaciones de widgets vuelven al hilo gráfico mediante `Clock`. El escáner limita la concurrencia para evitar saturar Binance. Los perfiles se guardan en JSON dentro del directorio privado de la aplicación.

## Interpretación de la calidad

La cifra `Calidad técnica /100` sigue siendo un índice interno de acuerdo entre factores, no una probabilidad garantizada de acierto. La interfaz lo expresa de forma explícita.

## Inicio

```powershell
python -m pip install -r requirements.txt
python main.py
```

Para ejecutar las pruebas:

```powershell
python -m pip install -r requirements-dev.txt
pytest -q
```
