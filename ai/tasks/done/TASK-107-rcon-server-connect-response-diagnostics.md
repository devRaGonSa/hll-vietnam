# TASK-107-rcon-server-connect-response-diagnostics

## Goal
Diagnosticar y resolver el bloqueo real que impide la captura RCON efectiva en entorno real, ahora acotado al stage `server_connect_response`.

## Context
El proyecto ya valido lo siguiente:
- la conectividad TCP a los 3 targets RCON funciona
- el loader/config de targets ya normaliza correctamente `name` y `external_server_id`
- la captura RCON sigue fallando en los 3 targets con:
  - `error_type = "timeout"`
  - `error_stage = "server_connect_response"`
- por eso siguen en cero:
  - `rcon_historical_samples`
  - `rcon_historical_competitive_windows`
- y, como consecuencia, `historical server summary` y `recent historical matches` siguen usando fallback a `public-scoreboard`

Esto sugiere que el problema pendiente ya no esta en la app de arbitraje ni en el loader, sino en la respuesta real del protocolo/servicio RCON del lado servidor o en su disponibilidad efectiva.

## Scope
Diagnostico tecnico e integracion minima necesaria.
No rehacer frontend.
No reabrir TASK-105.
No cerrar TASK-106 hasta que exista cobertura RCON real verificable.

## Steps
1. Auditar:
   - `backend/app/rcon_client.py`
   - `backend/app/rcon_historical_worker.py`
   - configuracion efectiva de targets y timeout
   - documentacion operativa RCON existente en la repo
2. Confirmar que significa exactamente un timeout en `server_connect_response` dentro del flujo HLL RCON:
   - TCP abierto pero sin respuesta util al `ServerConnect`
   - puerto incorrecto
   - servicio RCON no habilitado
   - password/protocolo incompatibles
   - firewall/NAT/rate-limit/intermediario
3. Anadir, si hace falta, instrumentacion minima adicional para distinguir mejor:
   - conexion abierta pero sin payload
   - payload invalido
   - cierre prematuro
   - respuesta no compatible con el protocolo esperado
4. Preparar checklist operativa clara para validar con quien administre los servidores:
   - puerto RCON correcto
   - RCON habilitado realmente
   - password correcta
   - compatibilidad del protocolo esperado
   - exposicion accesible desde Docker/backend
5. Definir criterio de exito real:
   - al menos un target produce muestras validas
   - `rcon_historical_samples > 0`
   - `rcon_historical_competitive_windows > 0`
   - `summary` o `recent-matches` pueden pasar a `selected_source = "rcon"` con datos reales
6. Mantener honestidad explicita:
   - no cerrar TASK-106 si el problema sigue siendo externo/infradependiente y no hay cobertura real

## Constraints
- No fingir resolucion si la capa servidor sigue sin responder al protocolo
- No tocar frontend
- No mezclar esta task con cambios amplios de producto
- No romper fallback a `public-scoreboard`

## Validation
- El diagnostico deja claramente identificada la causa pendiente del fallo RCON real
- Existe una checklist operativa usable para validar el lado servidor
- Queda definido el criterio objetivo para cerrar TASK-106 con datos reales
- La repo queda consistente

## Expected Files
- `backend/app/rcon_client.py` solo si hace falta instrumentacion minima adicional
- `backend/app/rcon_historical_worker.py` solo si hace falta observabilidad minima adicional
- `backend/README.md` si hace falta documentar checklist/criterio de cierre
- o documentacion adicional minima si se considera mejor

## Outcome
- Auditados `backend/app/rcon_client.py`, `backend/app/rcon_historical_worker.py`,
  `backend/app/config.py`, `backend/.env.example`, `backend/README.md` y la
  documentacion RCON existente.
- Queda confirmado que `error_stage = "server_connect_response"` significa una
  frontera mas estrecha que un timeout generico:
  - `tcp_connect` ya se completo
  - el cliente ya envio `ServerConnect`
  - el bloqueo ocurre esperando la primera respuesta RCON del peer
- Se anadio instrumentacion minima en `backend/app/rcon_client.py` para
  distinguir mejor:
  - timeout esperando `response header`
  - timeout esperando `response body`
  - bytes parciales recibidos antes del timeout
  - cierre inesperado durante header/body
- Se documento en `backend/README.md` la interpretacion operativa exacta del
  fallo, una checklist usable para validar el lado servidor y el criterio
  objetivo de cierre real.
- La causa pendiente queda acotada a dependencias externas o de
  infraestructura/protocolo del lado servidor:
  - puerto RCON incorrecto o no asociado al servicio esperado
  - RCON no habilitado realmente
  - password o handshake/protocolo incompatibles
  - firewall/NAT/proxy/rate-limit que acepta TCP pero no deja pasar la
    respuesta aplicativa
- No se cierra TASK-106 con esta task: sin handshake valido y sin muestras
  reales, `summary` y `recent-matches` deben seguir usando fallback honesto.

## Validation Notes
- `python -m py_compile backend\\app\\rcon_client.py`
- Revision de `git diff --name-only` para confirmar que el trabajo de esta task
  quedo acotado a `backend/app/rcon_client.py`, `backend/README.md` y el propio
  movimiento/documentacion de la task, ignorando cambios previos no
  relacionados ya presentes en el worktree.
