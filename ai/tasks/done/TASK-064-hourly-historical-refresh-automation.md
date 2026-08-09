# TASK-064-hourly-historical-refresh-automation

## Goal
Automatizar la actualización histórica horaria para que el backend ejecute refresh de histórico cada hora y regenere snapshots al finalizar, manteniendo la web histórica al día sin intervención manual.

## Context
La capa histórica ya dispone de:
- refresh incremental de histórico
- regeneración de snapshots tras una ingesta correcta

El problema actual es operativo: ese refresh no se está ejecutando de forma periódica, por lo que la UI sigue mostrando partidas antiguas aunque el flujo técnico ya exista. La solución correcta es programar la ejecución horaria del refresh histórico y dejar que la regeneración de snapshots ocurra como parte natural del flujo, sin convertir esta fase en infraestructura final de producción.

## Steps
1. Revisar la implementación actual de refresh histórico y regeneración de snapshots.
2. Confirmar cómo se ejecuta hoy el flujo para:
   - `comunidad-hispana-01`
   - `comunidad-hispana-02`
   - `comunidad-hispana-03`
3. Diseñar una forma clara de ejecutar el refresh histórico cada hora para los tres servidores.
4. Asegurar que el flujo horario haga:
   - refresh histórico
   - regeneración de snapshots tras refresh correcto
5. Definir una forma práctica de dejarlo corriendo en:
   - entorno local
   - entorno Docker / Compose del proyecto
6. Documentar la operativa mínima:
   - cómo arrancarlo
   - cómo verificar que sigue corriendo
   - cómo comprobar que los snapshots se siguen actualizando
7. Mantener fuera del alcance:
   - infraestructura final de producción
   - TLS
   - dominio público
   - scheduler externo definitivo
8. Validar que la solución no dependa de regenerar snapshots sin refresh previo.
9. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/historical_ingestion.py
- backend/app/historical_runner.py
- backend/app/historical_snapshots.py
- docker-compose.yml
- README.md

## Expected Files to Modify
- backend/README.md
- backend/app/historical_runner.py
- docker-compose.yml
- README.md
- opcionalmente archivos de entorno de ejemplo o documentación técnica adicional si ayudan a dejar clara la automatización horaria

## Constraints
- No convertir esta task en infraestructura final de producción.
- No romper el flujo local actual del backend.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en refresh histórico horario y snapshots posteriores al refresh.

## Validation
- Existe una forma clara de ejecutar refresh histórico cada hora.
- El flujo contempla `#01`, `#02` y `#03`.
- La regeneración de snapshots ocurre después del refresh correcto.
- La documentación explica cómo dejarlo corriendo en local o Docker.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
