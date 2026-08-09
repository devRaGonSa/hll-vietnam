---
id: TASK-215
title: Optimize weekly and monthly ranking read path
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-215 - Optimize weekly and monthly ranking read path

## Goal

Optimizar la ruta publica de lectura de los rankings weekly y monthly para que lean exclusivamente snapshots ya materializados, evitando inicializacion, migracion o setup de storage en cada request publica y reduciendo la latencia del read path sin tocar frontend, assets ni Elo/MMR.

## Context

Tras `TASK-211` se corrigio la ruta anual para separar lectura publica de generacion/escritura. Ahora se ha detectado el mismo patron en weekly/monthly.

Evidencia de produccion:

- la API publica devuelve correctamente:
  - `snapshot_status = ready`
  - `read_model = ranking-snapshot`
  - `fallback_used = false`
  - `items = 20`
- el perfilado directo de:

```python
build_global_ranking_payload(
    timeframe="weekly",
    metric="kills",
    limit=20,
    server_id="all",
)
```

ha tardado `101.33 segundos`.

`cProfile` indica:

- `payloads.py:787 build_global_ranking_payload -> 101.330s`
- `rcon_historical_leaderboards.py:315 get_latest_ranking_snapshot -> 101.330s`
- `rcon_historical_leaderboards.py:98 initialize_ranking_snapshot_storage -> 101.306s`
- `rcon_admin_log_materialization.py:24 initialize_rcon_materialized_storage -> 101.294s`
- `postgres_rcon_storage.py:383 initialize_postgres_rcon_storage -> 101.315s`

La causa actual es que `get_latest_ranking_snapshot()` llama a `initialize_ranking_snapshot_storage()` dentro de una ruta publica de solo lectura. Esa funcion inicializa o migra storage y no debe ejecutarse durante una request publica que solo lee snapshots ya materializados.

Regla arquitectonica:

- los endpoints publicos de ranking weekly/monthly deben leer unicamente:
  - `ranking_snapshots`
  - `ranking_snapshot_items`
- no deben:
  - consultar RCON
  - consultar scoreboard publico
  - recalcular rankings en runtime
  - escanear `rcon_match_player_stats`
  - inicializar o migrar storage en request publico
  - hacer N+1 por jugador
  - preparar fallback runtime salvo modo interno explicito

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Revisar primero la implementacion actual en `backend/app/rcon_historical_leaderboards.py` y el ensamblado de payloads en `backend/app/payloads.py`.
2. Tomar como referencia conceptual la separacion aplicada en `TASK-211` para annual.
3. Separar con claridad:
   - inicializacion, generacion o escritura de snapshots
   - lectura publica de snapshots
4. Mantener `initialize_ranking_snapshot_storage()` disponible para:
   - generacion
   - refresh
   - CLI
   - procesos internos
   - SQLite legacy si realmente lo requiere
5. Evitar `initialize_ranking_snapshot_storage()` en `get_latest_ranking_snapshot()` cuando se use PostgreSQL por defecto.
6. En la ruta PostgreSQL publica:
   - abrir conexion directa con `connect_postgres_compat()`
   - buscar snapshot en `ranking_snapshots`
   - contar o listar `ranking_snapshot_items`
   - devolver payload sin inicializar storage
7. Mantener compatibilidad SQLite legacy explicita:
   - si `db_path` se pasa explicitamente, resolver path de solo lectura sin migrar o inicializar si el diseno actual lo permite
   - no romper tests existentes
8. Mantener el contrato de respuesta:
   - `read_model = ranking-snapshot`
   - `snapshot_status = ready`
   - `fallback_used = false`
   - `items` segun `limit`
   - weekly/monthly siguen funcionando para `all`, `comunidad-hispana-01` y `comunidad-hispana-02`
   - las metricas existentes siguen funcionando
9. Anadir un test unitario con monkeypatch o mock para verificar que `get_latest_ranking_snapshot()` no invoca `initialize_ranking_snapshot_storage()` en la ruta PostgreSQL de lectura publica, tomando como referencia el test creado en `TASK-211`.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/payloads.py`
- `ai/tasks/done/TASK-211-optimize-annual-ranking-read-path.md`

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-215-optimize-weekly-monthly-ranking-read-path.md`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/payloads.py`

Optional only if strictly necessary:

- backend unit test file related to ranking snapshots or payloads

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not overwrite repository-specific context with generic platform template text.
- No ejecutar `ai-platform run`.
- No tocar `frontend/`.
- No tocar assets de armas.
- No tocar SVGs.
- No modificar imagenes fisicas.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- No tocar `ai/system-metrics.md`.
- No hacer push.
- No consultar RCON, scoreboard publico ni recalcular ranking dentro de la lectura publica weekly/monthly.
- No escanear `rcon_match_player_stats` en la ruta publica weekly/monthly.
- No hacer N+1 por jugador en la ruta publica weekly/monthly.
- No inicializar ni migrar storage en request publico weekly/monthly.
- Los endpoints publicos deben leer read models propios en PostgreSQL.
- La lectura publica weekly/monthly debe leer exclusivamente `ranking_snapshots` y `ranking_snapshot_items`.
- Mantener compatibilidad con SQLite legacy solo como modo explicito si ya existe soporte real para ello.

## Validation

Before completing the task ensure:

- `get_latest_ranking_snapshot()` no invoca `initialize_ranking_snapshot_storage()` en la ruta PostgreSQL de lectura publica
- no aparece `initialize_ranking_snapshot_storage` en el perfil de la ruta publica
- no aparece `initialize_rcon_materialized_storage` en el perfil de la ruta publica
- no aparece `initialize_postgres_rcon_storage` en el perfil de la ruta publica
- la generacion o escritura de snapshots sigue pudiendo inicializar storage cuando sea necesario
- la lectura publica weekly/monthly no recalcula ranking ni cae a runtime aggregates
- la respuesta mantiene:
  - `read_model = ranking-snapshot`
  - `snapshot_status = ready`
  - `fallback_used = false`
  - `items` segun `limit`
- se ejecuta `compileall`:

```bash
python -m compileall backend\app\rcon_historical_leaderboards.py backend\tests\<test_file>.py
```

- se ejecuta el test unitario anadido
- se ejecuta esta medicion directa:

```bash
python - <<'PY'
import time
from app.payloads import build_global_ranking_payload

tests = [
    {"timeframe": "weekly", "metric": "kills", "limit": 20, "server_id": "all"},
    {"timeframe": "weekly", "metric": "kills", "limit": 30, "server_id": "all"},
    {"timeframe": "monthly", "metric": "kills", "limit": 20, "server_id": "all"},
]

for params in tests:
    for i in range(3):
        start = time.perf_counter()
        payload = build_global_ranking_payload(**params)
        elapsed = time.perf_counter() - start
        data = payload.get("data", payload)
        print({
            "params": params,
            "attempt": i + 1,
            "seconds": round(elapsed, 3),
            "items": len(data.get("items") or []),
            "snapshot_status": data.get("snapshot_status"),
            "read_model": (data.get("source") or {}).get("read_model"),
            "fallback_used": data.get("fallback_used"),
        })
PY
```

- si hay backend local accesible, se ejecuta esta medicion HTTP interna:

```bash
python - <<'PY'
import json
import time
from urllib.request import urlopen

urls = [
    "http://127.0.0.1:8000/api/ranking?timeframe=weekly&metric=kills&limit=20",
    "http://127.0.0.1:8000/api/ranking?timeframe=weekly&metric=kills&limit=30",
    "http://127.0.0.1:8000/api/ranking?timeframe=monthly&metric=kills&limit=20",
]

for url in urls:
    for i in range(3):
        start = time.perf_counter()
        with urlopen(url, timeout=30) as response:
            body = response.read()
        elapsed = time.perf_counter() - start
        payload = json.loads(body.decode("utf-8"))
        data = payload.get("data", {})
        print({
            "url": url,
            "attempt": i + 1,
            "seconds": round(elapsed, 3),
            "http": response.status,
            "items": len(data.get("items") or []),
            "snapshot_status": data.get("snapshot_status"),
            "read_model": (data.get("source") or {}).get("read_model"),
            "fallback_used": data.get("fallback_used"),
        })
PY
```

- weekly top 20 queda por debajo de `1 segundo`
- idealmente weekly top 20 queda por debajo de `300 ms`
- weekly/monthly siguen funcionando para `all`, `comunidad-hispana-01` y `comunidad-hispana-02`
- las metricas existentes siguen funcionando
- `git diff --name-only` matches the expected scope
- no unrelated files were modified

## Outcome

Result:

- Updated `backend/app/rcon_historical_leaderboards.py` to split public weekly/monthly snapshot reads from storage initialization and snapshot generation.
- Public reads now use a dedicated read-only connection helper:
  - PostgreSQL default path opens a direct compat read connection without `initialize_ranking_snapshot_storage()`
  - explicit SQLite legacy path resolves the file in read-only mode without migrations or setup
- Kept `initialize_ranking_snapshot_storage()` for generation, refresh, CLI and internal write flows.
- Tightened public ranking behavior so runtime fallback is no longer enabled by default; public requests only fall back when `HLL_BACKEND_RANKING_RUNTIME_FALLBACK_ENABLED` is explicitly enabled.
- Added `backend/tests/test_ranking_snapshot_payload.py` with a regression test asserting PostgreSQL public reads do not invoke ranking snapshot storage initialization.

Modified files:

- `ai/tasks/done/TASK-215-optimize-weekly-monthly-ranking-read-path.md`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/tests/test_ranking_snapshot_payload.py`

Cause fixed:

- `get_latest_ranking_snapshot()` initialized ranking snapshot storage before deciding the read path.
- On the PostgreSQL public read path that pulled in setup or migration work through:
  - `initialize_ranking_snapshot_storage()`
  - `initialize_rcon_materialized_storage()`
  - `initialize_postgres_rcon_storage()`
- The fix separates public snapshot reads from generation and prevents those initializers from appearing in the default public weekly/monthly read path.

Validation performed:

- PASS: `python -m compileall backend\app\rcon_historical_leaderboards.py backend\tests\test_ranking_snapshot_payload.py`
- PASS: `python -m unittest backend.tests.test_ranking_snapshot_payload`
- PASS: direct timing probe through `build_global_ranking_payload(...)`
- PASS: targeted `cProfile` probe confirms the profiled public read path now shows:
  - `build_global_ranking_payload`
  - `get_latest_ranking_snapshot`
  - and does not show:
    - `initialize_ranking_snapshot_storage`
    - `initialize_rcon_materialized_storage`
    - `initialize_postgres_rcon_storage`
- INFO: HTTP probe against `http://127.0.0.1:8000` could not run because the local backend was not listening (`ConnectionRefusedError`).
- INFO: local SQLite had no persisted weekly/monthly snapshots available:
  - `ranking_snapshots = 0`
  - `ranking_snapshot_items = 0`
  - because of that, local payload validation exercised the fast missing-snapshot public path, not a ready snapshot payload with items.

Before/after timing summary:

- Before, per production evidence:
  - `build_global_ranking_payload(timeframe="weekly", metric="kills", limit=20, server_id="all")` took `101.33 s`
- After, local direct payload timing:
  - weekly limit 20: `0.002 s`, `0.001 s`, `0.001 s`
  - weekly limit 30: `0.001 s`, `0.001 s`, `0.001 s`
  - monthly limit 20: `0.001 s`, `0.001 s`, `0.001 s`
- Local response contract after the change in this environment:
  - `snapshot_status = missing`
  - `read_model = ranking-snapshot`
  - `fallback_used = false`
  - `items = 0`
- Note: the `ready/items>0` contract could not be revalidated locally because no ranking snapshots existed in local storage.

Scope confirmation:

- No frontend file was touched.
- No weapon asset was touched.
- No SVG was touched.
- No physical image was modified.
- Elo/MMR was not reactivated.
- Comunidad Hispana #03 was not reintroduced.
- `ai/system-metrics.md` was not touched.
- No push was made.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
