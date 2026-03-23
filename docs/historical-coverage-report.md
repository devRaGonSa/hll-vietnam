# Historical Coverage Report

## Validation Date

- 2026-03-21
- 2026-03-23

## Scope

Estado real de la cobertura historica persistida localmente en
`backend/data/hll_vietnam_dev.sqlite3` tras ejecutar el bootstrap CRCON con el
flujo reforzado de `backend/app/historical_ingestion.py`.

## Commands Used

Desde `backend/`:

```powershell
python -m app.historical_ingestion bootstrap --max-pages 3 --detail-workers 16
```

Bootstrap acotado y reanudable para `comunidad-hispana-03`:

```powershell
python -m app.historical_ingestion bootstrap --server comunidad-hispana-03 --page-size 10 --max-pages 1 --detail-workers 8
```

Verificacion puntual previa de idempotencia sobre la primera pagina ya
importada:

```powershell
python -m app.historical_ingestion bootstrap --max-pages 1 --detail-workers 8
```

Esa reejecucion devolvio `matches_inserted: 0` y solo `matches_updated` para
los matches ya persistidos, confirmando el comportamiento idempotente en el
tramo reimportado.

## Source Depth Discovered

La propia API CRCON reporto en pagina 1:

- `comunidad-hispana-01`: `23029` matches historicos disponibles
- `comunidad-hispana-02`: `18221` matches historicos disponibles

Esto confirma que la fuente publica tiene un archivo mucho mas profundo que la
semana movil usada por la UI y que un bootstrap completo real es una operacion
larga incluso con paralelismo.

## Persisted Coverage After Bootstrap Validation

### comunidad-hispana-01

- matches importados: `150`
- jugadores unicos: `3986`
- filas de estadisticas por jugador: `12650`
- primera partida persistida: `2026-03-04T22:11:18Z`
- ultima partida persistida: `2026-03-20T21:41:18Z`
- rango cubierto: `15.98` dias

### comunidad-hispana-02

- matches importados: `150`
- jugadores unicos: `4468`
- filas de estadisticas por jugador: `12665`
- primera partida persistida: `2026-03-01T16:59:10Z`
- ultima partida persistida: `2026-03-20T21:14:21Z`
- rango cubierto: `19.18` dias

### comunidad-hispana-03

- matches importados: `33`
- jugadores unicos: `1161`
- filas de estadisticas por jugador: `2547`
- primera partida persistida: `2026-02-24T18:16:11Z`
- ultima partida persistida: `2026-03-08T18:11:52Z`
- rango cubierto: `12.0` dias
- total descubierto en la fuente publica: `11652` matches
- checkpoint actual de bootstrap: `next_page = 2`, `last_completed_page = 1`

## Interpretation

- La base persistida ya supera claramente la ventana semanal en ambos
  servidores, por lo que la UI historica ya puede distinguir entre "ranking de
  ultimos 7 dias" y "cobertura total importada" sin fingir que ambos conceptos
  son lo mismo.
- `comunidad-hispana-03` ya no esta vacio: existe historico real persistido,
  snapshots de resumen y partidas recientes, y un checkpoint reanudable para
  seguir ampliando cobertura sin repetir desde cero.
- El historico local sigue siendo parcial respecto al total reportado por la
  fuente. Lo importado hoy es suficiente para seguir con semantica y revisiones
  de UI, pero no representa aun el archivo completo disponible en CRCON.

## Source Limits Observed

- Bajo replays repetidos del mismo bootstrap, la fuente CRCON devolvio errores
  `502 Bad Gateway` intermitentes en `get_public_info` y `get_map_scoreboard`.
- Con `--detail-workers 16` la carga validada fue estable para `3` paginas por
  servidor. Con concurrencia mas alta se observaron payloads no validos con mas
  frecuencia.

## Operational Conclusion

- El bootstrap queda reanudable por checkpoint persistido en
  `historical_backfill_progress`; si no se pasa `--start-page`, una nueva
  sesion continua desde `next_page`.
- Cada pagina completada actualiza por servidor:
  - `last_completed_page`
  - `next_page`
  - `discovered_total_matches`
  - `discovered_total_pages`
  - `last_run`
- La estrategia operativa razonable para completar todo el archivo es ejecutar
  varias sesiones consecutivas con el mismo comando hasta que
  `archive_exhausted` pase a `true`.
- `--start-page` se conserva solo como override manual cuando haga falta
  reprocesar un tramo concreto.
- Mientras no se complete todo el archivo, cualquier UI o API debe mostrar la
  cobertura importada como cobertura real disponible y no como historico total
  del servidor.
