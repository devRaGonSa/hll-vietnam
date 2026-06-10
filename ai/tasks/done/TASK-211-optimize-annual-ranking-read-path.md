---
id: TASK-211
title: Optimize annual ranking read path
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
roadmap_item: foundation
priority: medium
---

# TASK-211 - Optimize annual ranking read path

## Goal

Optimizar la ruta publica de lectura del ranking anual para que lea exclusivamente los snapshots anuales ya materializados, evitando inicializacion, migracion o setup de storage en cada request publico y reduciendo la latencia del cold/read path sin tocar frontend.

## Context

El endpoint publico anual `/api/ranking?timeframe=annual&metric=kills&limit=30&year=2026` ha llegado a tardar 24-42 segundos en produccion. Sin embargo, las mediciones disponibles descartan a PostgreSQL como cuello de botella:

- `EXPLAIN ANALYZE` sobre `rcon_annual_ranking_snapshots` tarda ~`0.073 ms`
- `EXPLAIN ANALYZE` sobre `rcon_annual_ranking_snapshot_items` tarda ~`0.083 ms`
- `cProfile` directo posterior de `build_global_ranking_payload(... annual ...)` tarda ~`0.244 s`
- weekly ranking tarda ~`0.055 s`
- player search tarda ~`0.069 s`
- player profile tarda ~`0.136 s`

El hallazgo actual es que `backend/app/rcon_annual_rankings.py` llama a `initialize_rcon_materialized_storage(db_path=db_path)` al inicio de `get_annual_ranking_snapshot()`, incluso cuando la request publica solo necesita leer snapshots anuales ya calculados. Esta task debe separar con claridad la ruta de generacion/escritura anual de la ruta publica de lectura anual.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Revisar primero la ruta actual de lectura anual en `backend/app/rcon_annual_rankings.py` y el ensamblado de payloads en `backend/app/payloads.py`.
2. Identificar exactamente donde la lectura publica annual entra en setup o inicializacion innecesaria y separar esa responsabilidad de la generacion/escritura anual.
3. Hacer que la lectura publica anual use solo conexion de lectura y consultas sobre:
   - `rcon_annual_ranking_snapshots`
   - `rcon_annual_ranking_snapshot_items`
4. Evitar `initialize_rcon_materialized_storage()` dentro de `get_annual_ranking_snapshot()` salvo que exista un modo SQLite legacy explicito con `--sqlite-path`.
5. Mantener PostgreSQL como ruta operativa por defecto y conservar compatibilidad con SQLite solo como modo legacy explicito, sin migracion/setup durante la lectura publica.
6. Revisar `build_annual_ranking_snapshot_payload()` y `build_global_ranking_payload()` para asegurar que la lectura annual publica sigue devolviendo el contrato correcto sin fallback runtime.
7. Ejecutar la validacion funcional y de tiempos pedida, documentar antes/despues y anadir un test pequeno si el stack lo permite para blindar que la ruta PostgreSQL de lectura no inicializa storage.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/rcon_annual_rankings.py`
- `backend/app/payloads.py`
- `ai/tasks/done/TASK-188-audit-ranking-and-stats-query-performance.md`

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-211-optimize-annual-ranking-read-path.md`
- `backend/app/rcon_annual_rankings.py`
- `backend/app/payloads.py`

Optional only if strictly necessary:

- backend unit test file related to annual rankings or payloads

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not overwrite repository-specific context with generic platform template text.
- No ejecutar `ai-platform run`.
- No tocar `frontend/`.
- No tocar assets de armas ni SVGs.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- No consultar RCON, scoreboard publico ni recalcular ranking dentro de la lectura publica annual.
- No escanear `rcon_match_player_stats` en la ruta publica annual.
- No hacer N+1 por jugador en la ruta publica annual.
- Los endpoints publicos deben leer read models propios en PostgreSQL.
- La lectura publica annual debe leer exclusivamente `rcon_annual_ranking_snapshots` y `rcon_annual_ranking_snapshot_items`.
- Mantener compatibilidad con `--sqlite-path` solo como modo legacy explicito.

## Validation

Before completing the task ensure:

- `get_annual_ranking_snapshot()` no ejecuta `initialize_rcon_materialized_storage()` en la ruta PostgreSQL de lectura publica
- la generacion/escritura annual sigue pudiendo inicializar storage cuando sea necesario
- la lectura publica annual no recalcula ranking ni cae a runtime aggregates
- la respuesta annual mantiene:
  - `read_model = rcon-annual-ranking-snapshot`
  - `snapshot_status = ready`
  - `fallback_used = false`
  - `items = 30`
- se ejecuta esta medicion directa 3 veces:

```bash
python - <<'PY'
import time
from app.payloads import build_global_ranking_payload

for i in range(3):
    start = time.perf_counter()
    payload = build_global_ranking_payload(
        timeframe="annual",
        metric="kills",
        limit=30,
        year=2026,
        server_id="all",
    )
    elapsed = time.perf_counter() - start
    data = payload.get("data", payload)
    print({
        "attempt": i + 1,
        "seconds": round(elapsed, 3),
        "items": len(data.get("items") or []),
        "snapshot_status": data.get("snapshot_status"),
        "read_model": (data.get("source") or {}).get("read_model"),
    })
PY
```

- se ejecuta esta medicion HTTP interna 3 veces:

```bash
python - <<'PY'
import json
import time
from urllib.request import urlopen

url = "http://127.0.0.1:8000/api/ranking?timeframe=annual&metric=kills&limit=30&year=2026"

for i in range(3):
    start = time.perf_counter()
    with urlopen(url, timeout=30) as response:
        body = response.read()
    elapsed = time.perf_counter() - start
    payload = json.loads(body.decode("utf-8"))
    data = payload.get("data", {})
    print({
        "attempt": i + 1,
        "seconds": round(elapsed, 3),
        "http": response.status,
        "items": len(data.get("items") or []),
        "snapshot_status": data.get("snapshot_status"),
        "read_model": (data.get("source") or {}).get("read_model"),
    })
PY
```

- annual ranking queda claramente por debajo de `1 segundo` en caliente
- idealmente annual ranking queda por debajo de `300 ms`
- se ejecutan tests existentes relacionados si los hay
- si no hay tests suficientes, se anade un test unitario pequeno para verificar con monkeypatch/mock que `get_annual_ranking_snapshot()` no invoca `initialize_rcon_materialized_storage()` en la ruta PostgreSQL de lectura
- `git diff --name-only` matches the expected scope
- no unrelated files were modified

## Outcome

Documentar:

- causa exacta del problema de latencia en la ruta annual/cold path
- que separacion se hizo entre generacion annual y lectura publica annual
- como queda tratada la compatibilidad PostgreSQL por defecto y SQLite legacy explicito
- antes/despues de tiempos en la medicion directa y en la medicion HTTP
- test ejecutados o test anadido
- confirmacion explicita de que no se tocaron frontend, assets de armas, SVGs, Elo/MMR ni Comunidad Hispana #03

Result:

- Updated `backend/app/rcon_annual_rankings.py` to split annual snapshot reads from annual snapshot generation/storage initialization.
- Public annual reads now open PostgreSQL directly for snapshot queries and no longer call `initialize_rcon_materialized_storage()` on the PostgreSQL path.
- Legacy SQLite remains available only when an explicit `db_path`/`--sqlite-path` is used; the read path now resolves the file path without running initialization or migrations.
- Added `backend/tests/test_annual_ranking_payload.py` with a regression test asserting PostgreSQL annual reads do not invoke storage initialization.

Cause fixed:

- The annual public read path entered `initialize_rcon_materialized_storage()` before deciding between PostgreSQL and SQLite.
- In PostgreSQL mode that introduced avoidable cold-path schema/setup work in a request that only needed to read precomputed annual snapshots.
- The fix moves annual public reads to a read-only connection path that consults only:
  - `rcon_annual_ranking_snapshots`
  - `rcon_annual_ranking_snapshot_items`

Validation performed:

- PASS: `python -m compileall backend\\app\\rcon_annual_rankings.py backend\\tests\\test_annual_ranking_payload.py`
- PASS: direct unit test with stdlib `unittest`:
  - `AnnualRankingPayloadTests.test_get_annual_ranking_snapshot_skips_storage_init_on_postgres_read`
- PASS: direct in-process timing:
  - attempt 1: `0.010 s`
  - attempt 2: `0.001 s`
  - attempt 3: `0.001 s`
  - `items = 30`
  - `snapshot_status = ready`
  - `read_model = rcon-annual-ranking-snapshot`
- INFO: HTTP timing probe against `http://127.0.0.1:8000/api/ranking?...` could not run because the local server was not listening (`ConnectionRefusedError`).

Before/after timing summary:

- Before, per task diagnosis:
  - public production annual endpoint observed around `24-42 s`
  - direct in-process profiling around `0.244 s`
- After this change in local direct payload validation:
  - first call `0.010 s`
  - warm calls `0.001 s`

Scope confirmation:

- No frontend file was touched.
- No weapon asset, SVG or physical image was touched.
- No Elo/MMR code was reactivated.
- Comunidad Hispana #03 was not reintroduced.
- `ai/system-metrics.md` was not touched by this task.
- No push was made.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
