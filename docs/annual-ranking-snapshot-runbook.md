# Runbook: annual ranking snapshot top 20 (Stats)

Objetivo: operar el ranking anual top 20 de `Stats` de forma reproducible, usando snapshots precomputados para no recalcular anualmente por cada request.

## 1) Proposito del snapshot anual top 20

El snapshot anual proporciona la tabla de posiciones de jugadores para el bloque de ranking anual de `Stats` con impacto bajo en latencia y costo de consulta.

Objetivos del diseno:

- entregar `top 20` de la temporada por metrica (V1: `kills`);
- consumir un resultado estable desde API publica sin recalcular toda la historia anual en cada request;
- permitir validacion operativa clara de si el ranking esta disponible o no;
- soportar regeneracion controlada por proceso de mantenimiento.

## 2) Fuente de datos

La fuente oficial para este ranking es materializada RCON:

- `rcon_materialized_matches`
- `rcon_match_player_stats`

Filtro principal:

- `matches.source_basis = admin-log-match-ended`

Reglas clave de calculo:

- ventanas por ano (`YYYY-01-01T00:00:00Z` a `YYYY+1-01-01T00:00:00Z`);
- acumulado de `kills`, `deaths`, `teamkills` por `player_id`;
- orden por `metric_value` desc, `matches_considered` desc, `player_name` asc;
- solo posiciones con actividad valida y `player_name` no vacio.

## 3) Endpoint consumidor

Desde Stats se consume:

- `GET /api/stats/rankings/annual?year=<year>&server_id=<server-or-all>&metric=kills&limit=20`

En V1:

- `metric` soporta solo `kills`;
- `server_id` acepta `all` o identificador de servidor.

## 4) Como generar snapshot anual

La generacion se hace fuera de la API (job/comando) para precomputar:

1. Definir ano objetivo `year`.
2. Definir alcance `server_id` (`all` para global o servidor especifico).
3. Ejecutar generador de snapshot anual con la configuracion necesaria.
4. Generador:
   - elimina snapshot previo del mismo `(year, server_id, metric)` si existe;
   - recalcula top-k desde datos materializados RCON;
   - guarda cabecera + items del ranking en tablas snapshots;
   - persiste metadatos (`generated_at`, ventana y conteo fuente).

### Comando recomendado

```bash
python -m app.rcon_annual_rankings generate --year 2026 --server-key all-servers --metric kills --limit 30 --replace-existing
```

Notas:

- Cuando `HLL_BACKEND_DATABASE_URL` esta configurado, el comando usa PostgreSQL por defecto.
- SQLite queda solo como override explicito mediante `--sqlite-path <path>`.
- El comando puede fallar si la capa de datos local no esta inicializada.
- En entornos manuales, validar entorno y storage objetivo antes de ejecutar.
- Si no hay datos, se puede generar un snapshot vacio (`ready` con `items=[]`).

### Override local SQLite

```bash
python -m app.rcon_annual_rankings generate --year 2026 --server-key all-servers --metric kills --limit 30 --replace-existing --sqlite-path backend/data/hll_vietnam_dev.sqlite3
```

### Comando Docker recomendado

```bash
docker compose exec backend python -m app.rcon_annual_rankings generate --year 2026 --server-key all-servers --metric kills --limit 30 --replace-existing
```

## 5) Como regenerarlo

Regenerar cuando:

- cambie la cobertura de datos anual;
- se detecte snapshot incompleto;
- se requiera refrescar fecha `generated_at`.

Procedimiento:

1. Ejecutar nuevamente el generador con el mismo `year` y `server_id`.
2. Aceptar reemplazo seguro del snapshot existente.
3. Validar que el snapshot nuevo refleje el recuento de partidas fuente actualizado.

Recomendacion:

- programar recalculo en ventanas de mantenimiento (idealmente cierre anual o rutina periodica definida por operaciones).

## 6) Como validar que existe un snapshot

Verificacion local:

1. Consultar API de ranking anual del ano objetivo.
2. Revisar `snapshot_status` en respuesta:
   - `ready`: existe snapshot;
   - `missing`: no existe snapshot.
3. Verificar `generated_at`, `window_start`, `window_end`, `source_matches_count`.
4. Verificar metadatos de limite:
   - `requested_limit`: limite pedido por el cliente;
   - `snapshot_limit`: limite persistido en snapshot;
   - `effective_limit`: limite realmente servido;
   - `item_count`: filas actualmente disponibles.

Se considera snapshot existente si API responde `snapshot_status="ready"`.

## 7) Como validar desde API

Usar llamadas directas a backend para validar estado y contenido:

- `GET /api/stats/rankings/annual?year=2026&server_id=all&metric=kills&limit=20`
- `GET /api/stats/rankings/annual?year=1999&server_id=all&metric=kills&limit=20`
- `GET /api/stats/rankings/annual?year=2026&server_id=all&metric=deaths&limit=20`

Checklist:

- HTTP 200 esperado para parametros validos de V1.
- `status` debe ser `"ok"` con estructura de data consistente.
- Para snapshots `ready`, `effective_limit` puede ser menor que `requested_limit` cuando el snapshot fue generado con un limite menor o contiene menos filas.
- En V1 con `metric` no soportada, esperar error de request (400) sin recomputar ranking.

## 8) Como validar desde frontend Stats

Desde `frontend/stats.html`:

1. Abrir la pestana `Stats`.
2. Ejecutar consulta anual usando `year`.
3. Confirmar:
   - estado de mensaje de carga/success/empty/error;
   - render de filas cuando haya items;
   - texto explicito cuando el snapshot esta `missing`;
   - texto explicito cuando el snapshot existe pero no tiene items.
4. Confirmar que no rompe bloque semanal/mensual ni busqueda cuando el anual no esta disponible.
5. Si endpoint retorna metricas invalidas, validar estado de warning en UI y que no cambia el resto del flujo.

## 9) Casos esperados

### 9.1 `snapshot_status=ready` con items

Respuesta tipica:

- `status: "ok"`
- `data.snapshot_status: "ready"`
- `data.items` con ranking ordenado.

Debe mostrarse top 20 con campos minimos:

- `ranking_position`
- `player_name`
- `metric_value`
- `matches_considered`
- `kills`
- `deaths`
- `teamkills`
- `kd_ratio`

### 9.2 `snapshot_status=ready` sin items

Respuesta tipica:

- `snapshot_status: "ready"`
- `items: []`
- `generated_at` puede estar presente

Debe renderizar estado "snapshot ready vacio" y no tratarlo como error de sistema.

### 9.3 `snapshot_status=missing`

Respuesta tipica:

- `snapshot_status: "missing"`
- `items: []`

Debe mostrar estado informativo claro de que el ranking no fue generado aun.

### 9.4 Metrica no soportada

Respuesta tipica:

- error request (400) con mensaje de metrica invalida/no soportada.

La UI/backend no debe intentar recalcular ni degradar a comportamiento inesperado.

## 10) Advertencias operativas

- No reactivar Elo/MMR ni logica dependiente en este bloque.
- No reintroducir `Comunidad Hispana #03` como alcance normal.
- No usar scoreboard publico como fuente primaria si RCON materializado esta disponible.
- No recalcular ranking anual completo en cada request publico; siempre leer snapshot.
- No tocar `frontend/assets/js/partida-actual.js` ni `frontend/assets/img/clans/bxb.png` en este runbook.

## Checklist de operacion

- [ ] Definir ano/servidor/limite.
- [ ] Ejecutar generacion o regeneracion.
- [ ] Confirmar respuesta de API por ano objetivo.
- [ ] Confirmar estado en UI de Stats.
- [ ] Registrar fecha/hora de generacion y responsable.
- [ ] Si faltan datos esperados, revisar pipeline RCON materializado.

## Validacion de la task

- `docs/annual-ranking-snapshot-runbook.md` actualizado.
- Cambios esperados unicamente de documentacion.
- No se aplican tests automaticos en este runbook; la validacion real se ejecuta en la task de backend correspondiente.

## Proximos pasos recomendados

- Si el bloque muestra estados esperados y refrescos, conectar este runbook con operacion de mantenimiento programada.
- Mantener la misma politica de fuentes en futuros reportes o automatizaciones de jobs.
