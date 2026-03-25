# TASK-089-rcon-prospective-historical-capture-foundation

## Goal
Implementar una base de captura historica prospectiva por RCON que empiece a persistir datos hacia delante sin sustituir todavia `public-scoreboard` y sin prometer recuperacion retroactiva de periodos ya perdidos.

## Context
Esta task depende del diseno aprobado en la task anterior.

El objetivo aqui no es “rehacer todo el historico por RCON” en un solo paso, sino dejar una primera capacidad operativa para recoger telemetria historica hacia delante desde los targets RCON configurados.

La captura debe:
- vivir fuera del request path HTTP
- persistir datos con trazabilidad y checkpoints
- convivir con el historico actual basado en `public-scoreboard`
- ser util aunque al principio no cubra todas las metricas competitivas

## Steps
1. Revisar el diseno de `docs/rcon-historical-ingestion-design.md`.
2. Crear una capa de almacenamiento propia para historico prospectivo RCON:
   - tablas o estructuras separadas del historico `historical_*` actual
   - trazabilidad por servidor, run y checkpoint
3. Extender el cliente/provider RCON solo en la medida aprobada por el diseno:
   - sin asumir comandos no auditados
   - sin mezclar live state puntual con historico persistido
4. Crear un worker o runner dedicado de captura prospectiva RCON.
5. Permitir ejecucion:
   - manual de una pasada
   - periodica por bucle local o Compose
6. Añadir configuracion explicita para:
   - targets
   - intervalo
   - reintentos
   - timeouts
7. Añadir metadata de estado minima y runbook en README.
8. Mantener `public-scoreboard` como fuente historica por defecto hasta que exista una capa de lectura historica RCON util.

## Files to Read First
- `docs/rcon-historical-ingestion-design.md`
- `backend/README.md`
- `backend/app/data_sources.py`
- `backend/app/providers/rcon_provider.py`
- `backend/app/rcon_client.py`
- `backend/app/config.py`
- `docker-compose.yml`

## Expected Files to Modify
- `backend/app/config.py`
- `backend/app/data_sources.py`
- `backend/app/providers/rcon_provider.py`
- `backend/app/rcon_client.py`
- uno o varios archivos nuevos bajo `backend/app/` para worker/storage/run tracking
- `backend/README.md`
- opcionalmente `docker-compose.yml` si conviene dejar un servicio dedicado

## Constraints
- No reemplazar todavia `public-scoreboard` como fuente historica principal.
- No tocar la UI.
- No romper `/api/servers` live por RCON.
- No prometer backfill retroactivo.
- Mantener separada la telemetria prospectiva RCON del historico importado actual.
- No introducir dependencias externas innecesarias.

## Validation
- Existe una pasada manual funcional de captura prospectiva RCON.
- Existen checkpoints o run tracking.
- La persistencia queda separada y consistente.
- README documenta la operativa minima.
- La repo sigue pudiendo arrancar sin obligar a usar RCON historico.

## Change Budget
- Preferir menos de 9 archivos modificados o creados.
- Preferir menos de 420 lineas cambiadas.
