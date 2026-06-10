---
id: TASK-222
title: Fix historical match detail backend URL and false KPM
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Backend Senior
roadmap_item: foundation
priority: high
---

# TASK-222 - Fix historical match detail backend URL and false KPM

## Goal

Corregir `frontend/historico-partida.html` para que el detalle de una partida historica no intente conectar con `127.0.0.1:8000` en produccion y eliminar el KPM falso calculado con la duracion total de la partida.

## Context

La pagina de detalle historico lee `/api/historical/matches/detail?server=<server>&match=<match>`. En produccion, el frontend no debe usar `http://127.0.0.1:8000` como backend por defecto porque eso apunta al PC del usuario. Ademas, la tabla de jugadores mostraba KPM calculado como `kills / duration_seconds` de la partida completa, lo que no representa tiempo real jugado por jugador.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Leer primero los archivos listados y confirmar el fallback de backend y el uso de KPM.
2. Corregir la resolucion de URL de backend en `historico-partida.js` sin ampliar el alcance a otros modulos.
3. Confirmar que el detalle sigue llamando a `/api/historical/matches/detail?server=<server>&match=<match>`.
4. Eliminar de `historico-partida` la exposicion de KPM si no existe `player_active_seconds` real.
5. Validar sintaxis y revisar el alcance del diff.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- `docs/REAL_KPM_PLAYER_ACTIVE_SECONDS_DESIGN.md`

Tambien se revisaron:

- `frontend/assets/js/historico.js`
- `frontend/assets/js/historico-recent-live.js`
- `frontend/assets/js/ranking.js`
- `frontend/assets/js/config.js`
- `frontend/assets/css/historico.css`
- `ai/tasks/done/TASK-216-clean-ranking-ui-and-fix-kpm-metric.md`

## Expected Files to Modify

- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- `ai/tasks/done/TASK-222-fix-historical-match-detail-backend-url-and-false-kpm.md`

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not implement backend functionality unless frontend diagnosis proves it is necessary.
- No ejecutar `ai-platform run`.
- No hacer push.
- No tocar assets de armas.
- No tocar SVGs.
- No modificar imagenes fisicas.
- No tocar `ai/system-metrics.md`.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- No incluir cambios previos no relacionados.
- Mantener compatibilidad con desarrollo local si existe `data-backend-base-url`.
- No publicar KPM sin `player_active_seconds` real.

## Validation

Before completing the task ensure:

- `node --check frontend/assets/js/historico-partida.js`
- Si se tocan otros JS, `node --check` tambien.
- Validar por navegador o inspeccion que el detalle no intenta `127.0.0.1`.
- Confirmar que la llamada de detalle usa `/api/historical/matches/detail?server=<server>&match=<match>`.
- Validar que no queda texto KPM falso en `historico-partida`.
- `git diff --name-only` matches the expected scope, except pre-existing unrelated changes.
- Confirmar que no se tocaron backend, assets de armas, SVGs, imagenes fisicas ni `ai/system-metrics.md`.

## Outcome

Archivos modificados por esta task:

- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- `ai/tasks/done/TASK-222-fix-historical-match-detail-backend-url-and-false-kpm.md`

Causa exacta corregida:

- `frontend/historico-partida.html` tenia `data-backend-base-url="http://127.0.0.1:8000"`.
- `frontend/assets/js/historico-partida.js` usaba `document.body.dataset.backendBaseUrl || "http://127.0.0.1:8000"`.
- En produccion, esa combinacion podia construir llamadas contra el localhost del usuario. La pagina de detalle ya no define localhost en el HTML y el JS resuelve primero `data-backend-base-url` si existe, luego `window.HLL_FRONTEND_CONFIG.backendBaseUrl`, y si no hay configuracion usa URL relativa para `/api`.

Endpoint de detalle:

- Se confirmo que `historico-partida.js` mantiene la llamada a `/api/historical/matches/detail?server=<server>&match=<match>`.
- El backend local no estaba escuchando en `http://127.0.0.1:8000`, por lo que no se pudo obtener una respuesta real del endpoint local.
- No se toco backend porque el fallo confirmado en esta task era frontend y no hubo evidencia de error backend.

Decision sobre KPM falso:

- Se elimino KPM del detalle de partida hasta que exista `player_active_seconds` real.
- Se quitaron la opcion de orden `KPM`, la cabecera de columna `KPM`, la celda por jugador, el chip del panel ampliado y las funciones `formatKpm`/`getKpmValue`.
- `duration_seconds` permanece solo para mostrar la duracion de la partida en el marcador, no para calcular rendimiento por jugador.
- No se toco la logica de ranking `Kills/partida` corregida en `TASK-216`.

Otros fallbacks localhost detectados:

- Siguen existiendo paginas publicas con `data-backend-base-url="http://127.0.0.1:8000"` o JS que lee ese dataset en `stats`, `historico`, `ranking`, `partida-actual`, `index` y `historico-recent-live`.
- No se corrigieron en esta task para no ampliar alcance. `frontend/assets/js/config.js` ya tiene una capa de reescritura defensiva, pero esos puntos quedan como deuda de endurecimiento fuera de esta causa directa.

Validaciones ejecutadas:

- `node --check frontend/assets/js/historico-partida.js`
- `rg -n "KPM|getKpmValue|formatKpm|kpm|kills_per_minute|player_active_seconds" frontend/historico-partida.html frontend/assets/js/historico-partida.js`
- `rg -n "api/historical/matches/detail|server=|match=" frontend/assets/js/historico-partida.js`
- `Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/api/historical/matches/detail?server=all-servers&match=__validation__' -TimeoutSec 5`
- `git diff --name-only`
- `git status --short -- ai/tasks/pending ai/tasks/in-progress ai/tasks/done frontend/historico-partida.html frontend/assets/js/historico-partida.js backend frontend/assets/img/weapons ai/system-metrics.md`

Resultado de validaciones:

- `node --check` paso sin errores.
- No queda texto ni funcion KPM en `historico-partida.html` ni `historico-partida.js`.
- La llamada de detalle conserva el endpoint esperado.
- La prueba HTTP local fallo con `No es posible conectar con el servidor remoto`; se documenta como backend local no disponible, no como fallo del endpoint.
- El navegador integrado no estaba disponible en esta sesion (`iab` no expuesto), asi que la validacion de red en navegador no pudo ejecutarse. La URL construida queda relativa cuando no hay backend configurado, por lo que ya no apunta a `127.0.0.1`.

Confirmacion de exclusiones:

- No se ejecuto `ai-platform run`.
- No se hizo push.
- No se hizo commit.
- No se toco backend.
- No se tocaron assets de armas.
- No se tocaron SVGs.
- No se modificaron imagenes fisicas.
- No se toco `ai/system-metrics.md`.
- No se reactivo Elo/MMR.
- No se reintrodujo Comunidad Hispana #03.
- No se incluyeron cambios previos no relacionados.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
