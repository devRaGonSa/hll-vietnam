# TASK-073-env-selection-docker-and-runbook-for-rcon

## Goal
Dejar documentado y operativo el cambio de fuente por entorno, incluyendo Docker/Compose y el runbook necesario para usar public-scoreboard en desarrollo y RCON en producción.

## Context
Una vez exista la capa de abstracción y el proveedor RCON, hace falta cerrar la parte operativa:
- variables de entorno
- selección de proveedor
- Docker/Compose
- documentación clara para desarrollo y despliegue

## Steps
1. Revisar el estado final de la abstracción y de ambos proveedores.
2. Documentar claramente:
   - modo dev con public-scoreboard
   - modo prod con RCON
3. Añadir o ajustar la configuración Docker/Compose necesaria para seleccionar proveedor por entorno.
4. Documentar variables sensibles y buenas prácticas para no versionar credenciales.
5. Asegurar que el runbook cubra:
   - arranque en dev
   - arranque en Docker
   - despliegue en prod con RCON
   - verificación básica de qué proveedor está activo
6. No convertir esta task en una guía de infraestructura final completa.
7. Mantener la documentación realista y alineada con lo implementado.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- README.md
- backend/README.md
- docker-compose.yml
- backend/app/config.py
- backend/app/source_provider.py
- backend.env.example

## Expected Files to Modify
- README.md
- backend/README.md
- docker-compose.yml
- backend.env.example o archivo equivalente
- opcionalmente docs/rcon-production-mode.md

## Constraints
- No documentar infraestructura inexistente.
- No exponer credenciales reales.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en selección por entorno y runbook.

## Validation
- La documentación explica con claridad cómo usar dev vs prod.
- Docker/Compose refleja la selección por entorno de forma razonable.
- Queda claro cómo verificar qué proveedor está activo.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.

## Outcome
- Se anadieron las variables de seleccion de proveedor y placeholders RCON a `backend/.env.example`.
- `docker-compose.yml` ahora propaga explicitamente la seleccion de proveedor y la configuracion RCON para backend e historical-runner.
- `README.md` y `backend/README.md` incluyen un runbook realista para dev, Docker y live con RCON.
- La verificacion operativa recomendada queda apoyada en `/health`, que expone los proveedores activos.

## Validation Notes
- `docker compose config` resolvio correctamente la configuracion final.
- La documentacion mantiene el limite actual del producto: RCON solo para live y `public-scoreboard` para historico.
- No se documentaron credenciales reales ni infraestructura no implementada en la repo.
