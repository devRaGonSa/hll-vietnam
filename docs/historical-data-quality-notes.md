# Historical Data Quality Notes

## Validation Date

- 2026-03-20

## Scope

Validacion local del historico CRCON persistido en `backend/data/hll_vietnam_dev.sqlite3`
para los servidores:

- `comunidad-hispana-01`
- `comunidad-hispana-02`

## Findings Before Correction

- habia jugadores fragmentados entre claves `steam:*`, `steaminfo:*`,
  `crcon-player:*` e incluso claves legacy sin prefijo
- algunas filas usaban `steaminfo.id` corto como si fuera `steam_id`, lo que no
  representaba un SteamID real
- existian partidas duplicadas por sesion cuando una partida en curso quedaba
  persistida con id sintetico y luego aparecia cerrada con id CRCON numerico
- el ranking semanal podia contar esas partidas transitorias porque aceptaba
  filas sin `ended_at`

## Corrections Applied

- la identidad de jugador ahora prioriza:
  - `steaminfo.profile.steamid`
  - `player_id` cuando ya parece un SteamID real
  - `player_id` como `crcon-player:*`
  - `steaminfo.id` solo como ultimo fallback
- la inicializacion del storage fusiona jugadores duplicados y reasigna sus
  estadisticas por partida
- la inicializacion del storage fusiona partidas duplicadas por
  `(servidor, started_at, mapa)` cuando la fila mas completa ya representa la
  partida final cerrada
- `weekly-top-kills` filtra solo partidas cerradas con `ended_at`

## Final Local Snapshot After Correction

- partidas historicas: `12`
- jugadores historicos: `510`
- filas `historical_player_match_stats`: `914`
- distribucion:
  - `comunidad-hispana-01`: `7` partidas, `487` jugadores unicos, `859` filas
  - `comunidad-hispana-02`: `5` partidas, `44` jugadores unicos, `55` filas

## Checks Performed

- sin duplicados por `steam_id`
- sin duplicados por `source_player_id`
- sin duplicados de nombre normalizado en el dataset local actual
- sin partidas abiertas restantes (`ended_at IS NULL`)
- sin duplicados por misma combinacion de servidor, `started_at` y mapa
- el ranking semanal devuelve resultados separados por servidor y basados solo
  en partidas cerradas dentro de la ventana movil de 7 dias

## Notes

- el volumen actual sigue siendo pequeno y claramente parcial; la calidad
  estructural queda validada, pero no sustituye un bootstrap historico mas
  profundo cuando se quiera construir UI historica propia
- siguen existiendo partidas con muy pocos jugadores en el dataset local
  actual; por ahora se conservan porque no son un problema de integridad, sino
  una caracteristica del muestreo ingerido hasta hoy
