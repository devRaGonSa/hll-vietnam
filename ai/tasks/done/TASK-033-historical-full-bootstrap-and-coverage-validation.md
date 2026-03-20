# TASK-033-historical-full-bootstrap-and-coverage-validation

## Goal
Ejecutar y consolidar una carga histórica completa real para los 2 servidores de la comunidad, validando la cobertura temporal y cuantitativa del histórico persistido para asegurar que la base histórica sea suficientemente representativa antes de seguir refinando la UI y las métricas.

## Context
La capa histórica ya existe y funciona, pero el estado actual del proyecto indica que el histórico persistido parece insuficiente para representar con credibilidad una semana completa de actividad. La UI actual muestra resúmenes basados en lo que haya cargado en la base, y si la cobertura es corta puede inducir a interpretar mal el estado del histórico. Antes de seguir afinando la capa histórica, hace falta asegurar un bootstrap real y comprobar la cobertura conseguida para ambos servidores.

## Steps
1. Revisar la implementación actual de bootstrap, refresh incremental y persistencia histórica.
2. Confirmar si el histórico actual está subpoblado por haber usado refrescos parciales, límites de páginas, validaciones locales u otras restricciones.
3. Ejecutar o dejar implementado el flujo de bootstrap completo real para ambos servidores de la comunidad, sin limitar la carga a una ventana artificialmente corta.
4. Persistir el histórico completo disponible desde la fuente CRCON scoreboard JSON para ambos servidores.
5. Verificar y documentar, por servidor:
   - número total de partidas históricas persistidas
   - número de jugadores únicos
   - rango temporal cubierto
   - fecha/hora de primera partida persistida
   - fecha/hora de última partida persistida
6. Validar que la persistencia sigue siendo idempotente tras el bootstrap completo.
7. Detectar si hay límites reales de origen (por ejemplo, datos antiguos no disponibles ya en la fuente) y documentarlos claramente.
8. Revisar si hace falta ajustar el flujo bootstrap para que sea operativamente reproducible y comprensible.
9. Documentar el estado real de cobertura alcanzado tras este bootstrap.
10. No crear todavía UI histórica nueva en esta task.
11. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/historical-crcon-source-discovery.md
- docs/historical-domain-model.md
- docs/historical-data-quality-notes.md
- backend/README.md
- backend/app/config.py
- backend/app/historical_ingestion.py
- backend/app/historical_storage.py
- backend/app/historical_models.py
- backend/app/routes.py
- backend/app/payloads.py

## Expected Files to Modify
- backend/README.md
- backend/app/historical_ingestion.py
- backend/app/historical_storage.py
- backend/app/config.py
- opcionalmente nuevos módulos auxiliares si son necesarios para consolidar bootstrap y validación de cobertura
- un documento técnico nuevo o actualizado, por ejemplo:
  - docs/historical-coverage-report.md
  - docs/historical-data-quality-notes.md

## Constraints
- No basar el histórico en A2S.
- No crear UI histórica nueva en esta task.
- No depender del HTML público de `/games` como fuente final.
- No romper el flujo actual de live status.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en bootstrap completo, cobertura e idempotencia.

## Validation
- Existe un bootstrap histórico completo real para ambos servidores.
- La cobertura histórica real queda medida y documentada.
- El histórico persistido contiene un volumen y rango temporal coherentes con la disponibilidad real de la fuente.
- La persistencia sigue siendo idempotente.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 7 archivos modificados o creados.
- Preferir menos de 260 líneas cambiadas.
