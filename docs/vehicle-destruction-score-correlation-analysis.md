# Análisis: inferencia de destrucción de vehículos en partida actual por correlación de puntuación de combate

## 1) Resumen ejecutivo

No hay evidencia en la arquitectura actual de un `combat_score` (ni `offense_score`, `defense_score`, `support_score` ni `total_score`) consultable **en vivo por jugador** para partidas en tiempo real.

Se puede inferir destrucción de vehículo solo con baja confianza a partir del AdminLog (`kill` + arma anti-tanque) y sin score delta en vivo.  

### Recomendación principal

Clasificación de viabilidad: **no viable sin nueva fuente** (para confirmación de destrucción de vehículo en partida actual).
- Viable parcialmente: generar **candidatos débiles** con evidencia de arma anti-tanque y metadatos de kill.
- No viable: confirmación robusta (`confirmed_adminlog_vehicle_event` o `score_delta_match`) bajo fuentes actuales.

---

## 2) Fuentes revisadas

- `backend/app/rcon_client.py`
- `backend/app/providers/rcon_provider.py`
- `backend/app/payloads.py`
- `backend/app/rcon_admin_log_parser.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/config.py`
- `backend/app/scoreboard_origins.py`
- `backend/app/rcon_scoreboard_correlation.py`
- `backend/app/providers/public_scoreboard_provider.py`
- `backend/app/rcon_historical_storage.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/tests/test_current_match_payload.py`
- `backend/tests/test_rcon_admin_log_parser.py`
- `frontend/assets/js/partida-actual.js` (solo consumo actual, sin cambios)

---

## 3) Qué datos tenemos hoy

### RCON en vivo
- `query_live_server_sample` consulta `GetServerInformation` y expone estado general del servidor (mapa, modo, tiempos, jugadores conectados/máximos, scores por equipo, etc.).
- No hay consulta de roster detallada ni endpoint en este flujo que devuelva métricas por jugador.

### AdminLog
- El parser ya reconoce `kill`, `message`, `connected`, `disconnected`, `team_switch`, `match_*`, `chat`, `kick`, `ban`.
- `kill` incluye `killer_*`, `victim_*`, `weapon` y timestamp aproximado.
- No existe evento explícito de tipo “vehicle_destroyed” ni campo dedicado de score en el evento.

### Almacenamiento histórico/persistencia
- Eventos y mensajes se guardan en `rcon_admin_log_events`.
- Hay metadata de jugador en eventos (incluyendo identificadores de jugador cuando parseable), y payloads sin schema de puntuación por componente.
- No hay snapshot de `combat_score` por jugador en `live` ni en tablas de snapshot del flujo actual.

### Scoreboard público
- `public_scoreboard_provider.py` consume endpoints tipo `get_public_info`, `get_scoreboard_maps`, `get_map_scoreboard`.
- No hay integración que entregue componente de score por jugador en vivo dentro del código actual.

---

## 4) Qué datos faltan para inferencia robusta de destrucción de vehículo

- Score por jugador en vivo al instante (combat/offense/defense/support/total).
- Snapshot continuo por jugador (`target_key`, `player_id`) con timestamps alineables al servidor.
- Evento de destrucción de vehículo explícito en AdminLog.
- Normalización confiable de daño/munición en AdminLog que distinga:
  - arma anti-tanque vs no anti-tanque,
  - kill a infantería vs kill por daño de vehicular.
- Fuente de verdad para tabla de puntos de recompensa por vehículo/arma (si no hay oficial).

---

## 5) Respuesta a preguntas clave

1. ¿Alguna fuente actual devuelve score por jugador en vivo?
   - `combat_score`, `offense_score`, `defense_score`, `support_score`, `total_score`: **no hay fuentes vivas por jugador identificadas en el flujo actual**.
   - `kills/deaths` por jugador en vivo: **no desde RCON live payload actual**, solo derivables de AdminLog offline/cron histórico.

2. ¿`query_live_server_sample` o client actual devuelven roster nominal o solo conteos?
   - Solo conteos/síntesis del servidor; **no roster nominal**.

3. ¿Scoreboard público expone API/página con stats por jugador en vivo?
   - No se encontró en el código actual una fuente dedicada a estadísticas en vivo por jugador.

4. ¿AdminLog incluye `player_id` en kills/messages/connected/team_switch?
   - Sí en eventos parseables (kill, connected, disconnected, team_switch), aunque `player_id` puede faltar o ser inconsistente por mensajes no normalizados.

5. ¿Se puede correlacionar de forma fiable un kill con snapshots de score?
   - Hoy por hoy: **no**, porque no hay snapshots de score por jugador en vivo.

6. ¿Granularidad temporal necesaria?
   - Para correlación por delta, se necesitan al menos snapshots cada `5s` (o menos idealmente) y tolerancia temporal acotada.

7. ¿Tablas temporales necesarias?
   - Sí, si se adopta inferencia:
   - `rcon_current_player_score_snapshots`
   - `rcon_vehicle_destruction_candidates`

8. ¿Campos mínimos a guardar?
   - Ver modelado propuesto en sección 8.

9. ¿Armas candidatas anti-tanque?
   - `BAZOOKA`, `PIAT`, `PANZERSCHRECK`, `AT MINE`, `ANTI-TANK MINE`, `SATCHEL`, `AT GUN`, `CANNON` y variantes normalizadas.

10. ¿Cómo evitar falsos positivos?
   - Usar reglas de confianza multi-factor y penalizar eventos con múltiples kills rápidas, sin score_delta, o cambios de identidad.

11. ¿Confianza de inferencia?
   - Depende de la evidencia:
   - `confirmed_adminlog_vehicle_event` (si aparece en futuro)
   - `score_delta_match`
   - `anti_tank_weapon_score_delta`
   - `anti_tank_weapon_only`

12. ¿Distinguir bazooka matando infantería vs destruyendo vehículo?
   - No de forma confiable con datos actuales.

13. ¿Distinguir mina antitanque vs antipersonal en AdminLog actual?
   - No con seguridad actual; se puede mejorar por normalización de texto de arma, pero queda incierto.

14. ¿Hay datos suficientes para delta de puntuación antes/después?
   - No. Falta captura continua de score por jugador en vivo.

15. ¿Cambios necesarios si la fuente existe?
   - Backend: nuevo collector de snapshots por jugador + normalizador de armas/eventos.
   - Worker: ventana de correlación, persistencia candidatos y limpieza.
   - Sin cambios frontend si el objetivo inicial es solo análisis de viabilidad.

---

## 6) Diseño propuesto si `combat_score` **sí existiera** (ideal)

### Esquema temporal 1: snapshots de score
- Al recibir cada sample live:
  - Capturar `combat_score`, `offense_score`, `defense_score`, `support_score`, `total_score` por jugador.
  - Persistir con `captured_at` y `server_time`.
  - Mantener ventana corta (1–3h) para memoria en caliente.

### Correlación
- Input: `kill` con arma anti-tanque.
- Buscar snapshot anterior en ventana `[-10s, 0s]` y posterior `[0s, +10s]`.
- Calcular delta y clasificar solo si salto cumple condiciones y hay contexto consistente.

### Decisión operativa sugerida
- Si la delta coincide con patrón fuerte y sin ruido: marca candidata de alta confianza.
- Si solo arma anti-tanque sin delta: candidata baja confianza.
- Si hay conflictos (multieventos) bajar confiabilidad o descartar.

---

## 7) Diseño alternativo si `combat_score` **no existe** (estado actual)

- Mantener estado actual sin feature productiva.
- Documentar y visualizar internamente solo candidatos débiles:
  - Evento kill con arma anti-tanque.
  - Co-ocurrencia de cambio de equipo/mapa/rounds en un rango temporal.
- No mostrar como “destrucción de vehículo” sin evidencia adicional.
- Guardar trazabilidad mínima para revisión manual futura.

---

## 8) Modelo de datos temporal propuesto

### Tabla: `rcon_current_player_score_snapshots`
- `id`
- `target_key`
- `player_id`
- `player_name`
- `team`
- `combat_score`
- `offense_score`
- `defense_score`
- `support_score`
- `total_score`
- `captured_at`
- `server_time`
- `source`
- `created_at`

### Tabla: `rcon_vehicle_destruction_candidates`
- `id`
- `target_key`
- `source_event_id`
- `event_timestamp`
- `server_time`
- `player_id`
- `player_name`
- `weapon`
- `score_before`
- `score_after`
- `combat_score_delta`
- `total_score_delta`
- `matched_score_bucket`
- `confidence`
- `evidence_json`
- `created_at`

### Retención recomendada
- Snapshots live: `1–3 horas`.
- Agregados agregados: no guardar indefinidamente; compactar por ventanas/ciclos.

---

## 9) Algoritmo de correlación before/after

1) Detectar evento `kill`.
2) Normalizar y clasificar arma (`AT`, ignorable, desconocida).
3) Obtener `player_id` del killer.
4) Buscar snapshot previo `[event_ts - 10s, event_ts]` (preferible el más cercano a `event_ts`).
5) Buscar snapshot posterior `[event_ts, event_ts + 10s]`.
6) Si existen ambos:
   - `delta = score_after - score_before` por componente y total.
7) Clasificar:
   - `confirmed_adminlog_vehicle_event`: si en el futuro aparece evento explícito.
   - `score_delta_match`: si delta positivo con patrón fuerte y único.
   - `anti_tank_weapon_score_delta`: AT + delta positivo compatible.
   - `anti_tank_weapon_only`: solo evento AT sin delta.
8) Ajustar confianza por ruido:
   - múltiples eventos en ventana,
   - falta de `player_id`,
   - desalineación temporal alta,
   - cambios de nombre/teams.

---

## 10) Ventanas temporales recomendadas

- Ventana principal: `[-10s, +10s]` respecto al kill.
- Ventana de captura de snapshots: `5s` entre muestras.
- Ventana de desempate:
  - Si hay múltiples eventos del mismo jugador en ±10s, reducir confianza.
  - Si hay 2+ snapshots en ventana, tomar snapshot más cercano al evento y registrar distancia temporal.

---

## 11) Armas anti-tanque candidatas

- `BAZOOKA`, `PIAT`, `PANZERSCHRECK`, `AT MINE`, `ANTI-TANK MINE`, `SATCHEL`, `AT GUN`, `CANNON`.
- `SATCHEL` puede aparecer como variantes de texto; normalizar case/espacios/dashes.
- Mantener lista configurable (diccionario de normalización) y tabla de excepciones.

---

## 12) Niveles de confianza y señales

- `high`: score delta consistente + evento AT + pocos eventos paralelos + match limpio de ventana temporal.
- `medium`: weapon AT + score delta parcial o sin un campo consistente.
- `low`: solo AT weapon sin delta.
- `invalid`: sin `player_id` ni evidencia de correlación temporal.

---

## 13) Riesgos y falsos positivos

- Misclasificación de kills de infantería con armas AT.
- Eventos AT en spam (misfires, intentos, daños no letales).
- Mismatches de identidad (`player_id` ausente o cambiante).
- Latencia entre `event_timestamp` y `server_time`.
- Diferencias entre entorno de servidor y extracción live.
- Suposición de valor fijo de puntuación por destrucción.

---

## 14) Consultas SQL de validación en producción/JTA

### a) Revisión de términos vehiculares en AdminLog
```sql
select event_type, count(*)
from rcon_admin_log_events
where raw_message ilike '%vehicle%'
   or raw_message ilike '%destroy%'
   or raw_message ilike '%destroyed%'
   or raw_message ilike '%tank%'
   or raw_message ilike '%truck%'
   or raw_message ilike '%halftrack%'
group by event_type
order by count(*) desc;
```

### b) Ejemplos de eventos relacionados con vehículo
```sql
select id, target_key, event_type, event_timestamp, raw_message
from rcon_admin_log_events
where raw_message ilike '%vehicle%'
   or raw_message ilike '%destroy%'
   or raw_message ilike '%destroyed%'
   or raw_message ilike '%tank%'
   or raw_message ilike '%truck%'
   or raw_message ilike '%halftrack%'
order by id desc
limit 50;
```

### c) Armas reales en kills (extract de payload JSON)
PostgreSQL con `jsonb`:
```sql
select parsed_payload_json->>'weapon' as weapon, count(*)
from rcon_admin_log_events
where event_type = 'kill'
group by parsed_payload_json->>'weapon'
order by count(*) desc;
```

Fallback no-`jsonb` (si `json`/texto):
```sql
select parsed_payload_json::text::json ->> 'weapon' as weapon, count(*)
from rcon_admin_log_events
where event_type = 'kill'
group by parsed_payload_json::text::json ->> 'weapon'
order by count(*) desc;
```

### c1) Top players con kills por weapon (validación adicional)
```sql
select parsed_payload_json->>'killer_name' as player, parsed_payload_json->>'weapon' as weapon, count(*) as kills
from rcon_admin_log_events
where event_type = 'kill'
group by 1,2
order by kills desc
limit 100;
```

---

## 15) Recomendación final

Con el estado actual del repositorio, la inferencia de destrucción de vehículo **no es confirmable en vivo**.  

Conclusión:
- `combat_score` en vivo por jugador: **no disponible** hoy.
- Por tanto, el score-delta **no puede implementarse hoy como verificación fuerte**.
- Se recomienda:
  1. Mantener esta tarea como análisis/documento.
  2. Validar si CRCON u otro canal puede proveer snapshots por jugador (`GetPlayers`/`GetPlayer`/endpoint oficial con score componentes).
  3. En caso afirmativo, implementar primero snapshots y luego pipeline de correlación con ventanas y niveles de confianza.
  4. Si no aparece fuente, continuar con señal heurística de baja confianza (AT kill only) sin presentación como destrucción confirmada.

### Nivel de viabilidad
- **No viable sin nueva fuente de score live** para detección fiable.
- **Viable parcialmente** para candidatos por heurística de arma + tiempo.

