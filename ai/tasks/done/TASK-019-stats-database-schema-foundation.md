# TASK-019-stats-database-schema-foundation

## Goal
Diseñar y dejar preparada la base del esquema de almacenamiento para snapshots y estadísticas iniciales de servidores de HLL actual, con una modelización genérica que pueda reutilizarse en el futuro para HLL Vietnam.

## Context
El proyecto necesita pasar de payloads placeholder a una arquitectura capaz de almacenar históricos. Antes de implementar colectores reales, es necesario definir un esquema de datos claro, neutro y extensible para snapshots de servidores y primeras métricas agregadas.

## Steps
1. Revisar la documentación técnica actual sobre backend, contratos y plan de ingesta.
2. Definir las entidades mínimas necesarias para la primera fase de persistencia. Incluir al menos:
   - game o source context si aplica
   - servers
   - server_snapshots
   - posibles tablas de agregación inicial o vistas documentadas para estadísticas
3. Asegurar que el naming sea genérico y reutilizable, evitando acoplar el modelo a Vietnam.
4. Definir para cada entidad:
   - propósito
   - campos principales
   - claves
   - relaciones
   - timestamps
5. Documentar qué datos deben persistirse por snapshot y cuáles pueden derivarse después.
6. Si el backend ya usa o prevé una tecnología concreta para persistencia, reflejarlo con claridad. Si aún no, documentar una base neutra y coherente.
7. Añadir o actualizar documentación técnica del repositorio para dejar claro el modelo inicial de almacenamiento.
8. Mantener el alcance en diseño y preparación, no en implementación completa de persistencia productiva.

## Files to Read First
- AGENTS.md
- docs/project-overview.md
- docs/roadmap.md
- docs/decisions.md
- docs/frontend-backend-contract.md
- docs/current-hll-data-ingestion-plan.md
- ai/repo-context.md
- ai/architecture-index.md
- backend/README.md
- backend/app/config.py
- backend/app/main.py

## Expected Files to Modify
- docs/decisions.md
- ai/architecture-index.md
- backend/README.md
- opcionalmente un nuevo documento técnico si encaja mejor, por ejemplo:
  - docs/stats-database-schema-foundation.md
- opcionalmente archivos base de estructura si el repositorio ya está preparado para ello, pero sin implementar una base de datos completa

## Constraints
- No implementar todavía la base de datos completa.
- No añadir migraciones productivas si la decisión técnica aún no está consolidada.
- No tocar frontend.
- No añadir integraciones reales de servidor.
- No hacer cambios destructivos.
- Mantener el modelo simple, genérico y preparado para crecer.

## Validation
- Existe un esquema de almacenamiento inicial claro para snapshots y estadísticas básicas.
- El naming es reutilizable para HLL actual y futuro HLL Vietnam.
- La documentación deja claro qué se persistirá primero y por qué.
- El resultado sirve como base directa para una siguiente task de colector de snapshots.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
