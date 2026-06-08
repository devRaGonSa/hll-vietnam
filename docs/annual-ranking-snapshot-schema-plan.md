# Annual Ranking Snapshot Schema Plan

Este documento define el diseño de persistencia para snapshots anuales top 20.

## 1. Objetivo del snapshot anual

- Evitar recalcular ranking anual completo por request público.
- Guardar ranking precomputado por año/servidor/métrica para consumo O(1) en API.
- Mantener continuidad con el pipeline materializado RCON ya existente (`rcon_materialized_matches` y `rcon_match_player_stats`).

## 2. Propuesta de tablas

Se plantea un modelo de dos tablas:

- `rcon_annual_ranking_snapshots`
- `rcon_annual_ranking_snapshot_items`

### `rcon_annual_ranking_snapshots`

Campos esperados:

- `id`
- `year`
- `server_key`
- `metric`
- `limit_size`
- `source_basis`
- `window_start`
- `window_end`
- `generated_at`
- `status`
- `source_matches_count`

### `rcon_annual_ranking_snapshot_items`

Campos esperados:

- `id`
- `snapshot_id`
- `ranking_position`
- `player_id`
- `player_name`
- `metric_value`
- `matches_considered`
- `kills`
- `deaths`
- `teamkills`
- `kd_ratio`

## 3. Propuesta de DDL (convencional SQLite/Postgres)

### SQLite

```sql
CREATE TABLE IF NOT EXISTS rcon_annual_ranking_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    server_key TEXT NOT NULL,
    metric TEXT NOT NULL,
    limit_size INTEGER NOT NULL DEFAULT 20,
    source_basis TEXT NOT NULL DEFAULT 'rcon-admin-log',
    window_start TEXT,
    window_end TEXT,
    generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'ready',
    source_matches_count INTEGER NOT NULL DEFAULT 0,
    source_range_start TEXT,
    source_range_end TEXT,
    source_payload_hash TEXT,
    generation_policy TEXT NOT NULL DEFAULT 'manual',
    notes TEXT,
    UNIQUE (year, server_key, metric),
    CHECK (limit_size > 0),
    CHECK (metric IN ('kills', 'deaths', 'matches_over_100_kills', 'support'))
);

CREATE INDEX IF NOT EXISTS idx_rcon_annual_snapshots_year
    ON rcon_annual_ranking_snapshots (year, server_key, metric);

CREATE INDEX IF NOT EXISTS idx_rcon_annual_snapshots_status
    ON rcon_annual_ranking_snapshots (status);

CREATE TABLE IF NOT EXISTS rcon_annual_ranking_snapshot_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL REFERENCES rcon_annual_ranking_snapshots(id) ON DELETE CASCADE,
    ranking_position INTEGER NOT NULL,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    metric_value INTEGER NOT NULL DEFAULT 0,
    matches_considered INTEGER NOT NULL DEFAULT 0,
    kills INTEGER NOT NULL DEFAULT 0,
    deaths INTEGER NOT NULL DEFAULT 0,
    teamkills INTEGER NOT NULL DEFAULT 0,
    kd_ratio REAL NOT NULL DEFAULT 0.0,
    generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(snapshot_id, ranking_position),
    UNIQUE(snapshot_id, player_id)
);

CREATE INDEX IF NOT EXISTS idx_rcon_annual_snapshot_items_snapshot
    ON rcon_annual_ranking_snapshot_items (snapshot_id, ranking_position);

CREATE INDEX IF NOT EXISTS idx_rcon_annual_snapshot_items_player
    ON rcon_annual_ranking_snapshot_items (snapshot_id, player_id);
```

### PostgreSQL (equivalente)

- `INTEGER` -> `INTEGER`
- `TEXT` -> `TEXT`
- `REAL` -> `DOUBLE PRECISION`
- `AUTOINCREMENT` -> `BIGSERIAL PRIMARY KEY` con secuencia estándar.
- `CURRENT_TIMESTAMP` con zona horaria (`TIMESTAMPTZ`) en la capa de compatibilidad.

## 4. Reglas de unicidad

1. Snapshot único por combinación:
   - `UNIQUE(year, server_key, metric)`.
2. Posición única por snapshot:
   - `UNIQUE(snapshot_id, ranking_position)`.
3. Jugador único por snapshot:
   - `UNIQUE(snapshot_id, player_id)`.

### Comportamiento esperado

- Si cambia el ranking de un año ya existente, el proceso de generación debe reemplazarlo de forma idempotente.
- El reemplazo puede implementarse con:
  - borrado por `snapshot_id` + inserción nueva, o
  - `UPSERT`/`ON CONFLICT` sobre `year + server_key + metric`.

## 5. Índices recomendados

#### `rcon_annual_ranking_snapshots`

- `(year, server_key, metric)` para lookup directo por API.
- `(server_key, status)` para monitorización y estado de caducidad.
- `(status, generated_at)` para refrescos y auditoría.

#### `rcon_annual_ranking_snapshot_items`

- `(snapshot_id, ranking_position)` para orden fijo del ranking.
- `(snapshot_id, player_id)` para comprobaciones de idempotencia.

## 6. Compatibilidad SQLite/Postgres

La implementación futura debe seguir el patrón actual:

- Consultas materializadas con SQL ANSI/SQLite friendly.
- Aislar la conexión con la función de compatibilidad existente:
  - `use_postgres_rcon_storage` + `connect_postgres_compat()`.
- Mantener placeholders por parámetro (`?` en SQL base, transformado por `PostgresCompatConnection`).

Esto evita duplicar lógica entre SQLite y Postgres y reduce riesgo al soportar ambas rutas.

### Ajuste de esquema en migración real (futuro)

- Incluir las tablas en `backend/app/postgres_rcon_storage.py` dentro de `RCON_SCHEMA_SQL` cuando corresponda.
- Añadir a `RCON_TABLES` en `backend/app/sqlite_to_postgres_migration.py` solo en fase de migración real.

## 7. Política de generación

### Inicial (ahora)
- Generación **manual**:
  - comando interno o mantenimiento administrativo para producir snapshot anual.
- Semántica de reemplazo:
  - `replace_existing` seguro por:
    - `UNIQUE(year, server_key, metric)` + transacción de borrado e inserción,
    - o `ON CONFLICT` en `INSERT`.
- Registrar:
  - `generated_at`, `status`, `source_matches_count`, `source_basis`.

### Evolución
- Generación programada futura (cron/job) con ventana anual cerrada.
- Mantener snapshots por año histórico para inspección.

## 8. API futura

Ruta definida para la siguiente implementación:

```http
GET /api/stats/rankings/annual?year=<year>&server_id=<server-or-all>&metric=kills
```

### Parámetros

- `year` (obligatorio): año calendario (ej. `2026`).
- `server_id`:
  - `all-servers` (default) o slug de servidor.
  - Debe mapearse al mismo `server_key` usado por RCON materialized.
- `metric` (obligatorio en la fase inicial): `kills`.

### Contrato recomendado

- `status: ok | pending | stale | not_found`.
- `data`:
  - `year`, `server_key`, `metric`, `generated_at`, `status`, `source_range_start`, `source_range_end`.
  - `items`: lista de items del ranking con los campos de la tabla de items.
- Si no hay snapshot generado:
  - respuesta `pending` (o `not_found`) con colección vacía.
  - sin recalcular on-demand (la carga debe dispararse por proceso dedicado).

## 9. Notas de alcance y migración

- Esta tarea es de diseño documental únicamente, no incluye migraciones ni cambios de código.
- No introduce Elo/MMR.
- No se añade lógica de frontend.
- No se modifica `frontend/assets/js/partida-actual.js`.
- No se toca `frontend/assets/img/clans/bxb.png`.
- No se reintroduce Comunidad Hispana #03.

