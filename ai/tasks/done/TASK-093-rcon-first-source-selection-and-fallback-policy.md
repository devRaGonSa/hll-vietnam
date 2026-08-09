# TASK-093-rcon-first-source-selection-and-fallback-policy

## Goal
Convertir la aplicación a una política RCON-first real para extracción de datos, manteniendo fallback automático a los métodos antiguos solo cuando RCON falle.

## Context
La repo ya tiene piezas RCON para live y captura prospectiva, pero todavía no está orientada a RCON-first por defecto.
Ahora mismo el sistema sigue arrancando con defaults antiguos y la política funcional real no coincide con el objetivo del producto.

Queremos:
- live/state de servidores -> RCON primero, A2S solo como fallback
- histórico/recopilación -> RCON primero, CRCON/public-scoreboard solo como fallback
- selección de fuente transparente, consistente y observable

## Steps
1. Auditar la selección actual de fuentes en:
   - `backend/app/data_sources.py`
   - `backend/app/payloads.py`
   - `backend/app/collector.py`
   - providers live e históricos actuales
   - `backend/app/rcon_historical_read_model.py`
2. Introducir una política explícita de “source arbitration” o equivalente:
   - RCON como fuente primaria
   - fallback a A2S para live si RCON falla
   - fallback a public-scoreboard/CRCON para histórico si RCON falla o no puede servir la operación concreta
3. Definir criterios claros de fallback:
   - error de red / timeout / auth / target no disponible
   - falta de cobertura o capacidad para una operación histórica concreta
4. Hacer que la respuesta backend deje trazabilidad clara:
   - fuente primaria intentada
   - fuente finalmente usada
   - si hubo fallback
   - motivo del fallback
5. Ajustar defaults/config para que el comportamiento por defecto del proyecto sea coherente con RCON-first.
6. Actualizar README con una sección clara:
   - política de prioridad de fuentes
   - casos de fallback
   - qué capacidades históricas siguen siendo parciales en RCON y cuándo entra CRCON/public-scoreboard

## Constraints
- No romper compatibilidad con los métodos antiguos.
- No eliminar A2S ni public-scoreboard.
- No tocar frontend salvo que haga falta exponer metadata mínima ya existente.
- Mantener el comportamiento observable y fácil de depurar.

## Validation
- El backend intenta RCON primero para live.
- Si RCON live falla, el backend cae a A2S de forma controlada.
- El backend intenta RCON primero para histórico.
- Si RCON histórico falla o no soporta una operación concreta, el backend cae a public-scoreboard/CRCON.
- Las respuestas reflejan qué fuente se usó realmente.
- README queda alineado con la política RCON-first.

## Expected Files
- `backend/app/data_sources.py`
- `backend/app/payloads.py`
- `backend/app/collector.py`
- providers/fuentes necesarias bajo `backend/app/`
- `backend/README.md`
- `backend/app/config.py` si hace falta para defaults explícitos
