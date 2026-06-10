---
id: TASK-223
title: Optimize historical match detail payload
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Frontend Senior
roadmap_item: foundation
priority: high
---

# TASK-223 - Optimize historical match detail payload

## Goal

Corregir la lentitud extrema de `/api/historical/matches/detail` para la partida historica RCON `comunidad-hispana-01:1781023156:1781028555:purpleheartlanewarfare`, que tarda alrededor de 55 segundos dentro del backend con 140 jugadores y provoca timeout/error publico.

## Context

La evidencia indica que el payload no es grande: unos 150 KB para 140 jugadores. La lentitud se produce durante la construccion del detalle, probablemente por enriquecimiento costoso o patron N+1 de perfiles/jugadores.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Perfilar `build_historical_match_detail_payload()` o `get_rcon_historical_match_detail()` para la partida problematica antes de cambiar codigo.
2. Identificar funciones lentas y confirmar si `profile_summary`, enlaces externos, `top_weapons`, `most_killed`, `death_by`, victims o nemesis generan trabajo por jugador.
3. Optimizar el detalle inicial para que sirva metadata, marcador y lista basica de jugadores sin enriquecimiento historico global pesado.
4. Mantener en el payload inicial las estadisticas de la partida que ya vengan del read model: kills, deaths, teamkills, KD, armas, abatidos y muertes por rival si no requieren queries extra.
5. Si `profile_summary` resulta costoso, quitarlo o hacerlo opcional en el detalle inicial y dejarlo para endpoint diferido futuro.
6. Confirmar que `historico-partida.js` sigue funcionando sin `profile_summary`.
7. Validar backend, frontend si se toca, endpoint interno y endpoint publico cuando sea posible.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/payloads.py`
- `frontend/assets/js/historico-partida.js`
- `ai/tasks/done/TASK-222-fix-historical-match-detail-backend-url-and-false-kpm.md`
- `docs/PERFORMANCE_PUBLIC_QUERY_AUDIT.md`

## Expected Files to Modify

- `backend/app/rcon_historical_read_model.py`
- `backend/tests/test_rcon_materialization_pipeline.py`
- `ai/tasks/done/TASK-223-optimize-historical-match-detail-payload.md`

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not run `ai-platform run`.
- Do not push.
- Do not touch weapon assets.
- Do not touch SVGs.
- Do not modify physical images.
- Do not touch `ai/system-metrics.md`.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not include unrelated previous changes.
- Do not introduce runtime RCON or scoreboard queries in the public request.
- Do not reintroduce false KPM.

## Validation

Before completing the task ensure:

- Profiling output before and after the backend change is recorded in the outcome.
- `python -m compileall backend/app` if backend is touched.
- Relevant backend tests run, or a small focused test is added if coverage is missing.
- `node --check frontend/assets/js/historico-partida.js` if frontend is touched.
- The problematic internal endpoint is measured and returns under 1 second if the local environment can reach the same data.
- The public endpoint is checked for 200/found=true if publicly reachable from the current environment.
- Visual validation confirms the detail page renders marcador, mapa and players and does not show KPM if a browser target is available.
- `git diff --name-only` matches expected scope, except pre-existing unrelated changes.
- Confirm excluded files/assets were not touched.

## Outcome

Archivos modificados por esta task:

- `backend/app/rcon_historical_read_model.py`
- `backend/tests/test_rcon_materialization_pipeline.py`
- `ai/tasks/done/TASK-223-optimize-historical-match-detail-payload.md`

Causa encontrada:

- En el path RCON materializado, `_build_materialized_detail_item()` cargaba siempre `get_latest_rcon_player_profile_summaries()` para todos los jugadores de la partida antes de devolver el detalle inicial.
- Ese enriquecimiento no pertenece al detalle basico de partida: trae historico global de perfil por jugador (`sessions`, `matches_played`, `favorite_weapons`, `victims`, `nemesis`, `averages`, `sanctions`) y parsea esos JSON para cada perfil devuelto.
- No se encontro N+1 en Python para `top_weapons`, `most_killed` o `death_by`: salen de JSON ya materializado en `rcon_match_player_stats` para esa partida.
- `external_profile_links` es barato: se deriva localmente desde `player_id` con `build_external_player_profile_fields()`, sin consulta extra.
- El patron lento confirmado por codigo queda en `profile_summary`, no en el tamano del payload ni en la renderizacion frontend.

Profiling ejecutado:

- Comando de perfil solicitado contra `build_historical_match_detail_payload()` para `comunidad-hispana-01:1781023156:1781028555:purpleheartlanewarfare`.
- En este entorno no estaba configurada la misma base PostgreSQL de produccion y Docker no estaba disponible (`docker compose ps` no pudo conectar con Docker Desktop), por lo que el perfil local cayo a fallback SQLite con `found=false`.
- Antes del cambio, perfil local disponible:
  - `seconds`: 5.333
  - `found`: false
  - `players`: 0
  - `source`: `historical-crcon-storage`
  - `fallback_used`: true
  - cuello local no representativo: `historical_storage.initialize_historical_storage()` y normalizacion SQLite legacy.
- Despues del cambio, perfil local disponible:
  - `seconds`: 3.644
  - `found`: false
  - `players`: 0
  - `source`: `historical-crcon-storage`
  - `fallback_used`: true
  - sigue sin ser medicion representativa de la partida RCON porque no alcanza el read model real.
- Evidencia inicial de produccion recibida para el caso real:
  - `seconds`: 55.137
  - `http`: 200
  - `bytes`: 150813
  - `players`: 140
  - `source`: `rcon-historical-competitive-read-model`
  - `fallback_used`: false

Solucion aplicada:

- El detalle inicial RCON ya no llama a `get_latest_rcon_player_profile_summaries()`.
- `_build_player_row()` ahora devuelve solo datos propios de la partida:
  - `player_name`
  - `team`
  - `kills`
  - `deaths`
  - `teamkills`
  - `kd_ratio`
  - `top_weapons`
  - `most_killed`
  - `death_by`
  - `external_profile_links` derivados localmente
- `profile_summary` queda diferido para una futura ruta lazy por jugador si se necesita mostrar historico global al expandir una fila.

Frontend:

- No se modifico `frontend/assets/js/historico-partida.js`.
- La UI ya no dependia de `profile_summary`; renderiza tabla y panel expandible con datos de partida, enlaces externos y mensajes `No disponible` cuando faltan listas ampliadas.
- No se reintrodujo KPM.
- La llamada relativa `/api/historical/matches/detail` se mantiene intacta.

Validaciones ejecutadas:

- `python -m compileall backend/app`
- `python -m unittest tests.test_rcon_materialization_pipeline.RconMaterializationPipelineTests.test_match_detail_omits_profile_summary_when_snapshot_exists`
- `python -m unittest tests.test_rcon_materialization_pipeline`
- Perfil local con `cProfile` antes y despues, documentado arriba.
- `Invoke-WebRequest` contra `http://127.0.0.1:8000/api/historical/matches/detail?...` fallo con `No es posible conectar con el servidor remoto`; no habia backend local escuchando.
- `docker compose ps` fallo porque Docker Desktop no estaba disponible en esta sesion.
- `git diff --name-only` revisado.

Resultado de validaciones:

- `compileall` paso.
- La suite `tests.test_rcon_materialization_pipeline` paso: 9 tests OK.
- La suite emite `ResourceWarning` de conexiones SQLite no cerradas ya existentes en esos tests, pero no falla.
- No se pudo validar el endpoint publico real ni visualmente por falta de URL publica absoluta/backend activo en este entorno.

Confirmacion de exclusiones:

- No se ejecuto `ai-platform run`.
- No se hizo push.
- No se hizo commit.
- No se tocaron assets de armas.
- No se tocaron SVGs.
- No se modificaron imagenes fisicas.
- No se toco `ai/system-metrics.md`.
- No se reactivo Elo/MMR.
- No se reintrodujo Comunidad Hispana #03.
- No se toco backend de rankings/snapshots.
- No se incluyeron cambios previos no relacionados. `git status` muestra cambios preexistentes en `ai/system-metrics.md`, assets de armas/SVGs y otros archivos no relacionados; esta task los dejo intactos.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
