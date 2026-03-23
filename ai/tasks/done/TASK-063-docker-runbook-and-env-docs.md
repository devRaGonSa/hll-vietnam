# TASK-063-docker-runbook-and-env-docs

## Goal
Documentar de forma clara cómo ejecutar el proyecto con Docker, qué variables de entorno utiliza y qué persistencia necesita, dejando una guía práctica para desarrollo y predespliegue.

## Context
Una containerización útil no queda cerrada solo con Dockerfiles y Compose; hace falta documentación clara para levantar el proyecto, entender los volúmenes, configurar entorno y evitar errores de operación.

## Steps
1. Revisar el estado final de la containerización del frontend y backend.
2. Documentar cómo construir y arrancar el proyecto con Docker.
3. Documentar variables de entorno relevantes del backend.
4. Documentar qué carpetas o volúmenes deben persistirse.
5. Incluir una guía breve para:
   - primer arranque
   - reinicio
   - regeneración de snapshots
   - backfill histórico dentro o fuera del contenedor si aplica
6. No convertir esta task en una guía de infraestructura final.
7. Mantener la documentación práctica y enfocada al estado real del proyecto.
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
- backend/app/historical_ingestion.py
- backend/app/historical_runner.py

## Expected Files to Modify
- README.md
- backend/README.md
- opcionalmente docs/docker-deployment.md
- opcionalmente archivos de ejemplo de entorno si ayudan a claridad

## Constraints
- No meter documentación ficticia.
- No describir infraestructura que aún no exista.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en un runbook realista para Docker.

## Validation
- La documentación explica cómo levantar el proyecto con Docker.
- Las variables y volúmenes relevantes quedan claras.
- Existe una guía útil para el flujo operativo básico.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
