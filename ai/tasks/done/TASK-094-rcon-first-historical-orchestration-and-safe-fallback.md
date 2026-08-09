# TASK-094-rcon-first-historical-orchestration-and-safe-fallback

## Goal
Reorientar la orquestación histórica para que RCON sea la vía principal de recopilación cuando esté disponible, dejando el flujo CRCON/public-scoreboard como fallback seguro y no como camino primario permanente.

## Context
Actualmente:
- existe `historical_runner`
- existe `rcon_historical_worker`
- existe locking single-writer
Pero la orquestación no representa todavía una estrategia RCON-first coherente.
Queremos una orquestación donde:
- la recopilación prospectiva por RCON sea la prioridad
- el refresh histórico clásico solo entre cuando RCON falle o no cubra la operación
- no haya starvation del lock por loops demasiado agresivos
- las automatizaciones sean operables en Docker sin bloquear trabajo manual innecesariamente

## Steps
1. Auditar:
   - `backend/app/historical_runner.py`
   - `backend/app/historical_ingestion.py`
   - `backend/app/rcon_historical_worker.py`
   - `backend/app/writer_lock.py`
   - `docker-compose.yml`
2. Definir una estrategia clara:
   - RCON historical capture como flujo primario
   - historical_ingestion clásico como fallback
   - snapshots/rebuilds alineados con esa política
3. Evitar que el worker RCON monopolice el writer lock:
   - revisar intervalos por defecto
   - revisar duración del trabajo por loop
   - revisar si conviene separar captura frecuente y rebuild menos frecuente
4. Asegurar que las pasadas manuales sean razonables:
   - si hay automatización activa, que el operador tenga mensajes claros
   - reducir riesgo de starvation o lock ocupado permanente
5. Mejorar el manejo de stale locks entre contenedores Docker si es necesario:
   - no depender solo del hostname si eso da falsos locks persistentes
   - mantener seguridad y evitar liberar locks válidos por error
6. Ajustar `docker-compose.yml` para que el stack quede alineado con el nuevo comportamiento por defecto.
7. Actualizar README/runbook:
   - qué proceso captura RCON primero
   - cuándo entra el fallback histórico clásico
   - cómo lanzar pasadas manuales
   - cómo interpretar locks ocupados

## Constraints
- No eliminar el locking compartido.
- No volver al comportamiento sin coordinación de writers.
- No dejar CRCON/public-scoreboard como camino principal encubierto.
- No romper la captura prospectiva RCON ya existente.

## Validation
- La automatización prioriza RCON para recopilación histórica.
- El flujo clásico entra solo como fallback.
- El lock compartido sigue funcionando.
- La operativa Docker no queda en starvation constante.
- Las pasadas manuales tienen comportamiento claro y documentado.
- README/runbook queda actualizado.

## Expected Files
- `backend/app/historical_runner.py`
- `backend/app/historical_ingestion.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/writer_lock.py`
- `docker-compose.yml`
- `backend/README.md`
- otros archivos backend si la orquestación lo requiere
