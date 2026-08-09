# TASK-072-rcon-provider-for-production

## Goal
Implementar un proveedor RCON para producción que permita usar acceso directo a los servidores como fuente principal de datos live e histórica, seleccionado por configuración sin alterar la UI.

## Context
La intención del proyecto es desplegar la web con acceso a los servidores mediante RCON. Eso debe convivir con el modo dev actual. El proveedor RCON debe quedar integrado en la nueva abstracción de fuentes y seleccionable por entorno.

## Steps
1. Revisar la abstracción de proveedor de datos ya creada.
2. Diseñar el proveedor RCON y la configuración necesaria para usarlo en producción.
3. Definir claramente qué capacidades cubrirá esta primera versión del proveedor RCON:
   - estado live de servidores
   - ingestión histórica o enriquecida, según lo que la integración permita hoy
4. Implementar el proveedor RCON sin romper el proveedor actual.
5. Añadir configuración por entorno para elegir:
   - public-scoreboard en dev
   - rcon en prod
6. Documentar variables necesarias, credenciales y limitaciones de la integración.
7. Mantener los contratos backend → frontend estables.
8. No introducir todavía una V2 del MVP ni persistencia extra de armas/duelos salvo que sea estrictamente necesario para dejar la integración operativa.
9. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/config.py
- backend/app/historical_ingestion.py
- backend/app/payloads.py
- backend/app/routes.py
- backend/app/source_provider.py
- documentación o librerías ya presentes para RCON si existen en la repo

## Expected Files to Modify
- backend/app/config.py
- backend/app/historical_ingestion.py
- backend/app/payloads.py
- backend/app/routes.py
- opcionalmente nuevos módulos, por ejemplo:
  - backend/app/providers/rcon_provider.py
  - backend/app/rcon_client.py
- backend/README.md
- opcionalmente backend/.env.example o backend.env.example

## Constraints
- No romper el modo dev actual.
- No exponer credenciales en la repo.
- No cambiar el contrato visible de la UI.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en el proveedor RCON de producción.

## Validation
- Existe un proveedor RCON seleccionable por configuración.
- El backend puede correr en modo dev con la fuente actual y en modo prod con RCON.
- La documentación deja claras variables y límites.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 7 archivos modificados o creados.
- Preferir menos de 260 líneas cambiadas.

## Outcome
- Se implemento `backend/app/rcon_client.py` con conexion TCP y cifrado XOR minimo para comandos HLL RCON.
- Se anadio `backend/app/providers/rcon_provider.py` como proveedor live seleccionable por configuracion.
- `/health` ahora expone `live_data_source` y `historical_data_source` para verificar el proveedor activo.
- Se mantuvo el modo dev actual y se documento la limitacion actual: el historico sigue dependiendo de `public-scoreboard`.

## Validation Notes
- `python -m compileall backend/app` completo sin errores.
- `build_health_payload()` devuelve correctamente los proveedores activos por defecto.
- La repo no contiene una canalizacion historica basada en eventos/logs RCON; por eso la parte historica RCON sigue quedando documentada como no operativa en esta version.
