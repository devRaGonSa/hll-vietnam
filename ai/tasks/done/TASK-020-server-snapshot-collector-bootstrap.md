# TASK-020-server-snapshot-collector-bootstrap

## Goal
Preparar un bootstrap técnico mínimo para un colector de snapshots de servidores en el backend Python, dejando la estructura lista para capturar y normalizar datos de HLL actual sin implementar todavía una ingesta completa de producción.

## Context
Tras definir la estrategia de ingesta y el esquema base de almacenamiento, el siguiente paso es dejar preparada la estructura mínima de un colector en backend. Esta task no debe resolver toda la persistencia ni depender de una fuente definitiva, pero sí debe sentar la base para un flujo futuro de captura periódica.

## Steps
1. Revisar la documentación de ingesta y esquema de almacenamiento.
2. Revisar la estructura actual del backend Python.
3. Crear una estructura mínima y clara para un colector o servicio de snapshots dentro de `backend/app/`.
4. Definir interfaces o funciones base para:
   - obtener datos crudos de una fuente
   - normalizar esos datos
   - producir un snapshot consistente
5. Si encaja con la fase actual, permitir una ejecución manual o de desarrollo del colector usando datos controlados.
6. Mantener la implementación desacoplada para que la fuente real pueda sustituirse más adelante sin romper el resto del backend.
7. Actualizar la documentación backend para explicar el papel del colector y cómo encaja con futuras estadísticas.
8. Mantener el alcance estricto: bootstrap técnico del colector, no pipeline completo de producción.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/current-hll-data-ingestion-plan.md
- docs/stats-database-schema-foundation.md
- backend/README.md
- backend/app/__init__.py
- backend/app/config.py
- backend/app/main.py
- backend/app/routes.py
- backend/app/payloads.py

## Expected Files to Modify
- backend/README.md
- backend/app/__init__.py
- opcionalmente archivos nuevos dentro de `backend/app/` si mejoran claridad, por ejemplo:
  - backend/app/collector.py
  - backend/app/normalizers.py
  - backend/app/snapshots.py
- opcionalmente documentación técnica relacionada si requiere alineación menor

## Constraints
- No implementar todavía una ingesta real completa.
- No depender de scraping productivo.
- No introducir una base de datos completa en esta task.
- No tocar frontend.
- No añadir complejidad innecesaria.
- No hacer cambios destructivos.
- Mantener la estructura clara y pequeña.

## Validation
- El backend contiene una base mínima para un colector de snapshots.
- La estructura separa captura, normalización y snapshot de forma razonable para la fase actual.
- La documentación backend refleja el nuevo estado.
- El resultado prepara el terreno para una siguiente task de persistencia real o ejecución periódica.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.
