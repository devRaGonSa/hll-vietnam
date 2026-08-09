# TASK-027-historical-crcon-source-discovery

## Goal
Descubrir y documentar la fuente historica real mas estable para los 2 servidores de la comunidad, basada en CRCON/scoreboard, dejando claro como obtener datos historicos reutilizables para futuras estadisticas semanales y evitando depender de una implementacion previa ya descartada.

## Context
El proyecto ya tiene resuelta la parte de estado actual de servidores mediante A2S para la landing. La siguiente fase es historico y estadisticas agregadas, por ejemplo "jugadores con mas kills de la ultima semana por servidor".

Se parte de dos hechos importantes:
1. El historico NO debe construirse con A2S como fuente principal, porque A2S sirve para estado actual y no para historico retroactivo de partidas.
2. Cualquier intento previo de historico semanal basado directamente en la pagina de la comunidad debe considerarse deshecho, invalido o no reutilizable como base de arquitectura para esta nueva fase.

Ademas, el analisis tecnico previo apunta a que la fuente correcta para historico debe venir de la capa CRCON/scoreboard publico de los servidores de la comunidad, o de la fuente estructurada que alimenta dicho scoreboard.

## Goal Detail
Esta task NO debe implementar todavia la ingesta historica final ni endpoints de rankings. Su mision es descubrir con precision de donde salen los datos historicos, como se accede a ellos y cual es la estrategia tecnica mas estable para las siguientes tasks.

## Steps
1. Revisar el estado actual del proyecto para confirmar que la parte historica previa basada directamente en la pagina comunitaria no debe tomarse como base valida.
2. Analizar las dos fuentes reales de historico asociadas a los servidores de la comunidad:
   - `https://scoreboard.comunidadhll.es/games`
   - `https://scoreboard.comunidadhll.es:5443/games`
3. Investigar como cargan los datos esas paginas:
   - peticiones XHR/fetch
   - posibles endpoints JSON
   - paginacion
   - URLs de detalle de partida
   - identificadores de match
   - identificadores o claves de jugador
   - filtros o parametros relevantes
4. Determinar si la fuente utilizable mas estable es:
   - una API/JSON expuesta por el scoreboard
   - una estructura HTML parseable
   - otra capa accesible derivada de CRCON
5. Documentar que datos historicos parecen estar realmente disponibles y estables. Incluir al menos:
   - servidor
   - partida
   - fecha/hora
   - mapa
   - jugador
   - kills
   - otras metricas relevantes si aparecen
6. Documentar riesgos y limites:
   - cambios de HTML
   - dependencia de endpoints privados o fragiles
   - ausencia de ids estables
   - paginacion o limites de historico
   - datos historicos posiblemente incompletos
7. Proponer la estrategia recomendada para las siguientes fases, distinguiendo claramente entre:
   - fuente historica ideal
   - plan operativo inicial realista
   - fallback si no existe API estructurada
8. Dejar explicito que NO debe hacerse:
   - no basar la arquitectura historica en A2S
   - no asumir como valida una implementacion previa ya revertida
   - no disenar todavia la UI historica
9. Actualizar la documentacion tecnica del repositorio con el resultado del discovery.
10. Al completar la implementacion:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/decisions.md
- docs/current-hll-servers-source-plan.md
- docs/frontend-backend-contract.md
- backend/README.md
- cualquier documentacion o codigo existente relacionado con historico, scoreboard o CRCON
- cualquier rastro de implementacion historica previa que haya quedado en el repositorio, solo para confirmar su descarte

## Expected Files to Modify
- ai/architecture-index.md
- docs/decisions.md
- opcionalmente backend/README.md si conviene reflejar el nuevo frente tecnico
- un nuevo documento tecnico, por ejemplo:
  - `docs/historical-crcon-source-discovery.md`

## Constraints
- No implementar todavia ingesta historica completa.
- No implementar todavia endpoints de rankings.
- No implementar todavia UI historica.
- No basar la arquitectura historica en A2S.
- No dar por buena ninguna implementacion historica previa que ya haya sido revertida o descartada.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en discovery tecnico y documentacion solida.

## Validation
- Existe documentacion clara sobre la fuente historica real de los 2 servidores.
- Queda claro si la fuente reutilizable es JSON/API, HTML parseable u otra capa.
- Quedan identificados los datos historicos realmente disponibles.
- Quedan documentados riesgos, limites y estrategia recomendada.
- No se ha implementado todavia ingesta o UI prematura.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 lineas cambiadas.

## Outcome
- Se documento que ambas URLs de scoreboard sirven una SPA y que la fuente historica reutilizable real es JSON bajo `baseURL: "/api"`.
- Se verificaron y documentaron los endpoints historicos observados:
  - `GET /api/get_public_info`
  - `GET /api/get_scoreboard_maps?page={page}&limit={limit}`
  - `GET /api/get_map_scoreboard?map_id={map_id}`
- Se confirmo que `get_scoreboard_maps` aporta listado paginado de partidas y que `get_map_scoreboard` aporta detalle de partida con `player_stats` y metricas como `kills`, `deaths`, `teamkills`, `kills_per_minute`, `weapons`, `team.side` y `level`.
- Se dejo documentado que el HTML de `/games` no debe ser la base tecnica de ingesta y que A2S sigue limitado al estado actual.
- Se dejo constancia de que un intento previo de historico semanal no es base valida porque `backend/app/payloads.py` referencia `.historical_storage` pero ese modulo ya no existe.
- Se actualizo `docs/decisions.md` y `ai/architecture-index.md` para alinear la arquitectura con esta discovery.

## Validation Result
- Ejecutado fuera del sandbox: inspeccion directa de `https://scoreboard.comunidadhll.es/games` y `https://scoreboard.comunidadhll.es:5443/games`.
- Resultado: ambas rutas devuelven la misma SPA shell con bundle `index-DvMfaBhO.js`.
- Ejecutado fuera del sandbox: extraccion del bundle frontend.
- Resultado: el helper HTTP usa `axios.create({ baseURL: "/api" })`.
- Ejecutado fuera del sandbox: `GET /api/get_public_info`, `GET /api/get_scoreboard_maps?page=1&limit=5` y `GET /api/get_map_scoreboard?map_id=...` en ambos scoreboards.
- Resultado: se confirmaron identificacion por servidor, paginacion, ids de partida y metricas historicas por jugador.
- Ejecutado localmente: revision de `backend/app/payloads.py` y busqueda de restos historicos con `rg`.
- Resultado: se detecto un rastro previo no reutilizable de `weekly_top_kills` apoyado en un modulo ausente.

## Decision Notes
- La siguiente fase debe ingerir primero el listado de partidas por scoreboard y despues el detalle por `map_id`, manteniendo separados los dos origenes de la comunidad.
- El plan operativo inicial debe persistir partidos y estadisticas por jugador en backend propio para calcular agregados semanales sin consultar el scoreboard en cada request.
