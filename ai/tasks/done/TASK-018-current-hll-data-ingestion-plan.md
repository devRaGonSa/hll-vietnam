# TASK-018-current-hll-data-ingestion-plan

## Goal
Definir la estrategia técnica de ingesta de datos para Hell Let Loose actual, usándolo como banco de pruebas del proyecto HLL Vietnam, con foco en servidores, snapshots e históricos básicos sin implementar todavía la ingesta real completa.

## Context
La landing ya muestra servidores actuales de HLL como contenido provisional y el backend ya dispone de una base API placeholder. El siguiente paso lógico es fijar cómo se obtendrán y normalizarán datos reales o semirrealistas de HLL actual para validar la arquitectura que más adelante podrá reutilizarse con HLL Vietnam.

## Steps
1. Revisar la documentación actual del proyecto relacionada con servidores, backend y evolución de datos.
2. Definir qué tipos de datos se quieren ingerir inicialmente desde HLL actual. Incluir al menos:
   - listado de servidores
   - estado online/offline
   - jugadores actuales
   - capacidad máxima
   - mapa actual si está disponible
   - timestamp de captura
3. Definir el concepto de snapshot de servidor y cómo se usará para construir histórico.
4. Documentar las posibles fuentes técnicas de ingesta para HLL actual, distinguiendo entre:
   - datos controlados/mock
   - fuente externa pública
   - consulta directa de servidor o capa intermedia
5. Documentar riesgos y límites:
   - disponibilidad de terceros
   - cambios de formato
   - rate limits
   - latencia
   - CORS
   - fiabilidad de datos
   - dependencia de scraping o APIs no oficiales
6. Proponer la arquitectura de ingesta por fases:
   - fase 1: payload controlado y estructura estable
   - fase 2: colector de snapshots con fuente real o casi real
   - fase 3: explotación histórica y estadísticas básicas
7. Dejar claro qué no se implementará todavía.
8. Actualizar la documentación técnica del repositorio para servir de base a las siguientes tasks de base de datos y colector.

## Files to Read First
- README.md
- AGENTS.md
- docs/project-overview.md
- docs/roadmap.md
- docs/decisions.md
- docs/discord-and-server-data-plan.md
- docs/current-hll-servers-source-plan.md
- docs/frontend-backend-contract.md
- ai/repo-context.md
- ai/architecture-index.md
- backend/README.md

## Expected Files to Modify
- docs/roadmap.md
- docs/decisions.md
- ai/architecture-index.md
- opcionalmente un nuevo documento técnico si encaja mejor, por ejemplo:
  - docs/current-hll-data-ingestion-plan.md

## Constraints
- No implementar todavía ingesta real.
- No modificar comportamiento visible del frontend.
- No añadir base de datos funcional en esta task.
- No añadir dependencias nuevas.
- No hacer cambios destructivos.
- Mantener el resultado centrado en planificación técnica reutilizable para futuro HLL Vietnam.

## Validation
- Existe una estrategia documentada de ingesta para HLL actual como banco de pruebas.
- Quedan definidos snapshots, fuentes posibles, riesgos y fases.
- La documentación deja claro cómo se conectará este trabajo con almacenamiento e históricos.
- La base sirve para una siguiente task de esquema de base de datos.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.
