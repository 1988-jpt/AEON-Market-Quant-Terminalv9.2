# AEON Market Quant Terminal V8.1 Mobile Pro

## Adaptación móvil implementada

- Navegación lateral convertida en cajón plegable para teléfonos.
- Botón táctil de menú con cierre automático al cambiar de pantalla.
- Barra superior dividida en cabecera y controles desplazables horizontalmente.
- Controles táctiles con altura mínima de 48 dp.
- Dashboard adaptable a teléfono, tablet y escritorio.
- Tarjetas reorganizadas automáticamente según ancho y orientación.
- Gráfico y panel de contexto apilados en pantallas estrechas o verticales.
- Compatibilidad con rotación vertical y horizontal (`orientation = all`).
- Barras del sistema conservadas para reducir solapamientos con notch y navegación.
- Versión unificada a 8.1.0.
- Solicitud de permiso de notificaciones en Android en tiempo de ejecución.
- Registro de errores durante el cierre del servicio en lugar de ocultarlos.

## Verificaciones

- Compilación sintáctica completa: correcta.
- Preflight Android: correcto.
- Pruebas automatizadas: 39 aprobadas, 1 omitida por falta de entorno gráfico Kivy.

## Prueba física pendiente

La disposición visual debe validarse instalando el APK en un teléfono real. La compilación está preparada para GitHub Actions, pero OpenGL, fuentes, notch y comportamiento exacto dependen del dispositivo.
