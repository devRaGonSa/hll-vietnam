# TASK-031-local-cors-alignment-for-frontend-dev

## Goal
Corregir y alinear la configuracion CORS del backend para permitir que el frontend local de desarrollo consuma la API desde origenes locales habituales sin caer en fallback por bloqueo del navegador.

## Context
El backend responde correctamente a `/health`, `/api/servers/latest` y `/api/servers/history`, y los snapshots reales A2S ya estan persistidos. Sin embargo, el frontend servido localmente con `python -m http.server 8080` no puede consumir la API porque el navegador bloquea las respuestas por falta de la cabecera `Access-Control-Allow-Origin` para `http://localhost:8080`.

La correccion debe centrarse en CORS de desarrollo local, sin cambiar la arquitectura funcional del producto.

## Steps
1. Revisar la configuracion actual de CORS del backend.
2. Confirmar como se comparan y validan los origenes permitidos.
3. Anadir soporte correcto para los origenes locales de desarrollo mas comunes, incluyendo al menos:
   - `http://localhost:8080`
   - `http://127.0.0.1:8080`
4. Revisar si tambien conviene permitir otros puertos locales habituales documentados por el proyecto, sin abrir el backend de forma innecesaria.
5. Asegurar que las respuestas GET del backend incluyan `Access-Control-Allow-Origin` cuando el origen este permitido.
6. Asegurar que el backend maneje correctamente `OPTIONS` si el flujo actual lo requiere.
7. Actualizar la documentacion del backend para dejar claro como probar frontend y backend juntos en local.
8. Mantener el alcance centrado en desarrollo local y correccion CORS.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- backend/README.md
- backend/app/config.py
- backend/app/main.py
- backend/app/routes.py
- frontend/assets/js/main.js

## Expected Files to Modify
- backend/README.md
- backend/app/config.py
- backend/app/main.py
- opcionalmente otros archivos backend si la logica CORS esta centralizada en otro sitio

## Constraints
- No tocar visualmente el frontend.
- No cambiar endpoints ni payloads.
- No introducir dependencias nuevas innecesarias.
- No hacer cambios destructivos.
- Mantener la solucion pequena y claramente orientada a desarrollo local.

## Validation
- Una peticion desde `http://localhost:8080` a `http://localhost:8000/api/servers/latest` ya no falla por CORS.
- Una peticion desde `http://127.0.0.1:8080` tambien funciona si se decidio soportarla.
- La landing deja de caer al fallback estatico cuando el backend esta disponible.
- La documentacion refleja como ejecutar el stack local correctamente.

## Change Budget
- Preferir menos de 4 archivos modificados.
- Preferir menos de 140 lineas cambiadas.

## Outcome
- `backend/app/config.py` amplia la allowlist CORS local por defecto para cubrir `http://localhost:8080` y `http://127.0.0.1:8080`, manteniendo tambien `null` y los origenes ya usados en `5500`.
- `backend/app/config.py` normaliza espacios y barras finales en `HLL_BACKEND_ALLOWED_ORIGINS` para que un override local no falle por formato.
- `backend/README.md` documenta la prueba local recomendada con `python -m app.main` y `python -m http.server 8080`, y deja explicito que origenes locales quedan soportados por defecto.
- No fue necesario cambiar `backend/app/main.py` ni `backend/app/routes.py` porque la emision de `Access-Control-Allow-Origin` y el manejo de `OPTIONS` ya estaban correctamente centralizados en el handler HTTP.

## Validation Result
- Ejecutado: validacion aislada desde Python levantando `app.main.create_server()` en `127.0.0.1:8010` dentro del mismo proceso.
- Resultado `GET` con `Origin: http://localhost:8080`: `200 OK`, `Access-Control-Allow-Origin: http://localhost:8080`, `Vary: Origin`.
- Resultado `GET` con `Origin: http://127.0.0.1:8080`: `200 OK`, `Access-Control-Allow-Origin: http://127.0.0.1:8080`, `Vary: Origin`.
- Resultado `OPTIONS` con `Origin: http://localhost:8080`: `204 No Content`, `Access-Control-Allow-Origin: http://localhost:8080`, `Access-Control-Allow-Methods: GET, OPTIONS`, `Access-Control-Allow-Headers: Content-Type`.
- Observacion de entorno: `127.0.0.1:8000` ya estaba ocupado por otro proceso ajeno a esta task, asi que la validacion final se hizo en `:8010` para comprobar exactamente el codigo modificado sin depender de ese proceso.

## Decision Notes
- Se mantuvo una allowlist cerrada de desarrollo local en lugar de abrir CORS globalmente, porque la task pedia corregir el flujo local sin introducir una configuracion de produccion prematura.
- No se anadieron puertos arbitrarios extra; se alineo la configuracion con `5500`, `8080` y `null`, que cubren los flujos locales ya usados o documentados por el proyecto.
