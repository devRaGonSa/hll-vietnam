---
id: TASK-213
title: Fix ranking layout and loading state
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Experto en interfaz
roadmap_item: foundation
priority: high
---

# TASK-213 - Fix ranking layout and loading state

## Goal

Corregir la UX del ranking publico en `frontend/ranking.html` para que filtros y tabla queden en una unica seccion, la carga no quede bloqueada cuando la API ya respondio, y el copy visible use `periodo` de forma consistente sin cambiar ningun contrato de API.

## Context

La API de ranking ya responde rapido para combinaciones reales de filtros:

- `/api/ranking?timeframe=weekly&metric=kills&limit=20` -> ~127 ms
- `/api/ranking?timeframe=weekly&metric=kills&limit=30` -> ~81 ms
- `/api/ranking?timeframe=monthly&metric=kills&limit=20` -> ~77 ms
- `/api/ranking?timeframe=annual&metric=kills&limit=20&year=2026` -> ~39 ms

Por tanto, el cuello de botella actual no esta en backend ni base de datos. El problema a resolver es frontend: estado de carga, renderizado, carreras entre peticiones, logica de actualizacion y separacion visual entre filtros y resultados.

La revision actual de `frontend/assets/js/ranking.js` ya muestra una posible causa probable que debe confirmarse y corregirse durante la ejecucion:

- la carga inicial depende de `refreshBackendHealth()` antes de disparar `loadRanking()`
- no existe proteccion simple contra request race
- el estado de carga y el render comparten rutas que pueden dejar la UI en un estado obsoleto o visualmente vacio aunque la API responda rapido

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Leer primero los archivos listados en esta task y confirmar el comportamiento actual de `ranking.html` y `ranking.js`.
2. Unificar filtros, ayuda, acciones, estado y tabla dentro de una unica card o seccion, eliminando la card separada `Resultados / Tabla activa`.
3. Cambiar el copy visible para usar `periodo` en lugar de `ventana` donde aplique en la UI de ranking.
4. Revisar `frontend/assets/js/ranking.js` completo y eliminar cualquier causa de retardo artificial o bloqueo de loading:
   - `setTimeout` innecesario
   - debounce excesivo
   - promesas no esperadas
   - render condicionado a estado obsoleto
   - loading que no se limpia en `finally` o `catch`
   - botones que quedan deshabilitados
   - render silenciosamente omitido
5. Anadir proteccion simple contra carreras con `currentRequestId` incremental o `AbortController`.
6. Garantizar que la ultima peticion lanzada sea la unica autorizada a pintar la tabla.
7. Mantener los contratos actuales de API y el comportamiento de carga automatica existente solo si sigue siendo inmediato y sin bloqueos.
8. Validar por sintaxis, inspeccion visual y comprobacion de respuestas reales o equivalentes del endpoint antes de cerrar la task.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `frontend/ranking.html`
- `frontend/assets/js/ranking.js`
- `frontend/assets/css/styles.css`
- `frontend/assets/css/historico.css`
- `ai/tasks/done/TASK-207-annual-ranking-default-load-and-kpm-columns.md`

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-213-fix-ranking-layout-and-loading-state.md`
- `frontend/ranking.html`
- `frontend/assets/js/ranking.js`
- `frontend/assets/css/styles.css`

Si `frontend/assets/css/historico.css` resulta estar afectando realmente a `ranking.html`, documentarlo primero y mantener cualquier cambio alli como ajuste minimo y justificado.

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not implement backend functionality unless the task explicitly requires it.
- Do not expand Elo/MMR, historical workers or RCON server #03 handling unless the task explicitly requires it.
- Do not overwrite repository-specific context with generic platform template text.
- No ejecutar `ai-platform run`.
- No tocar `backend/`.
- No tocar endpoints ni contratos de API.
- No tocar `frontend/assets/img/weapons/`.
- No tocar SVGs.
- No modificar imagenes fisicas.
- No tocar `ai/system-metrics.md`.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- No hacer `push`.
- No hacer `commit` en esta task.
- Mantener compatibilidad con apertura directa en navegador cuando aplique.

## Validation

Before completing the task ensure:

- `node --check frontend/assets/js/ranking.js`
- si se toca cualquier otro archivo JS, ejecutar `node --check` sobre cada JS modificado
- por inspeccion visual local:
  - filtros y tabla aparecen dentro de una unica card o seccion
  - ya no queda una card separada `Resultados / Tabla activa` vacia
  - `Top publico por periodo` aparece correctamente
  - `El ranking expone los resultados de los lideres. Para busqueda individual usa Estadisticas.` aparece correctamente
  - semanal, mensual y anual pintan resultados
  - cambiar a mensual no deja la UI bloqueada
  - `Actualizar ranking` dispara una sola peticion visible y pinta rapido
  - `Top 20` y `Top 30` funcionan si el backend los acepta por URL o por interfaz habilitada
- validar contra backend real o equivalente local que los endpoints siguen respondiendo con:
  - `status = ok`
  - `snapshot_status = ready`
  - `read_model = ranking-snapshot` o `rcon-annual-ranking-snapshot`
  - `fallback_used = false`
- `git diff --name-only` matches the expected scope
- no unrelated files were modified
- documentar explicitamente si no existe automatizacion adicional para esta validacion frontend

## Outcome

Archivos modificados:

- `frontend/ranking.html`
- `frontend/assets/js/ranking.js`
- `frontend/assets/css/styles.css`
- `ai/tasks/done/TASK-213-fix-ranking-layout-and-loading-state.md`

Causa probable encontrada en `frontend/assets/js/ranking.js`:

- la carga inicial dependia de `refreshBackendHealth()` antes de pedir `/api/ranking`
- no existia proteccion contra request race entre cambios rapidos de filtros
- el estado de carga se combinaba con limpieza temprana de superficie, dejando la UI vacia o aparentemente bloqueada aunque la API respondiera rapido

Resumen del layout nuevo:

- filtros, nota, acciones, estado, metadatos y tabla quedaron dentro de una sola card
- se elimino la card separada `Resultados / Tabla activa`
- el copy visible principal se actualizo a `Top publico por periodo`
- la descripcion pasa a `El ranking expone los resultados de los lideres. Para busqueda individual usa Estadisticas.`

Cambio funcional aplicado en frontend:

- `ranking.js` ya no espera `/health` para cargar el ranking inicial
- la carga inicial llama directamente a `/api/ranking`
- se anadio `currentRequestId` mas `AbortController`
- cada nueva peticion aborta la anterior y solo la ultima puede pintar
- el boton `Actualizar ranking` se deshabilita mientras la peticion activa esta en curso y siempre se limpia en `finally`
- durante loading ya no se vacia la tabla de forma agresiva antes de tener la nueva respuesta
- se anadio `Top 30` a la interfaz para alinear la UI con el endpoint validado en contexto

Validaciones ejecutadas:

- `node --check frontend/assets/js/ranking.js`
- revision de diff acotado con `git diff --name-only` sobre los archivos esperados
- intento de validacion HTTP local de:
  - `/api/ranking?timeframe=weekly&metric=kills&limit=20`
  - `/api/ranking?timeframe=weekly&metric=kills&limit=30`
  - `/api/ranking?timeframe=monthly&metric=kills&limit=20`
  - `/api/ranking?timeframe=annual&metric=kills&limit=20&year=2026`
- el backend local no estaba disponible en `http://127.0.0.1:8000`, por lo que esa validacion quedo bloqueada con `No es posible conectar con el servidor remoto`
- no existe en esta ejecucion una inspeccion visual automatizada del DOM; la comprobacion queda por lectura del marcado y de la logica aplicada

Confirmacion de exclusiones:

- no se tocaron `backend/`, endpoints ni contratos de API
- no se tocaron `frontend/assets/img/weapons/`, SVGs ni imagenes fisicas
- no se toco `ai/system-metrics.md`
- no se reactivo Elo/MMR
- no se reintrodujo Comunidad Hispana #03
- no se hizo `push`

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
