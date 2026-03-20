# TASK-006-discord-and-server-data-plan

## Goal
Definir la estrategia técnica inicial para obtener, modelar y exponer los futuros datos de Discord y de los servidores de juego en el proyecto HLL Vietnam, sin implementar todavía integraciones reales.

## Context
El proyecto ya dispone de una landing mínima, un backend Python bootstrap y un contrato inicial frontend-backend documentado. Antes de implementar endpoints reales o lógica de consumo en frontend, es necesario fijar un plan claro sobre qué datos se quieren mostrar, de qué fuentes podrían obtenerse, qué limitaciones existen y cuál será el orden recomendado de implementación.

## Steps
1. Revisar la documentación técnica actual del proyecto.
2. Identificar qué información tendría sentido mostrar en la web sobre Discord. Incluir al menos posibles bloques como:
   - enlace de invitación
   - nombre de la comunidad
   - estado o presencia aproximada si fuera viable
   - información pública útil para comunidad
3. Identificar qué información tendría sentido mostrar sobre los servidores de juego. Incluir al menos posibles bloques como:
   - nombre del servidor
   - estado online/offline
   - mapa actual o rotación si fuera viable
   - jugadores conectados
   - capacidad máxima
   - ping o metadatos similares si la fuente lo permite
4. Documentar las posibles fuentes de datos para Discord, distinguiendo claramente entre:
   - widget público
   - API o integraciones externas
   - bot propio
   - datos configurados manualmente
5. Documentar las posibles fuentes de datos para servidores de juego, distinguiendo claramente entre:
   - consultas al servidor
   - API externa
   - datos mock/placeholder
   - actualización manual
6. Documentar riesgos, límites y restricciones:
   - credenciales
   - rate limits
   - disponibilidad
   - seguridad
   - CORS
   - latencia
   - dependencia de servicios externos
7. Proponer una estrategia por fases:
   - fase inicial con placeholders o datos controlados
   - fase intermedia con integración técnica limitada
   - fase posterior con integración más real si procede
8. Dejar claro qué NO se implementará todavía.
9. Actualizar la documentación técnica del repositorio para que futuras tasks de backend y frontend tengan una base clara.

## Files to Read First
- README.md
- AGENTS.md
- docs/project-overview.md
- docs/roadmap.md
- docs/decisions.md
- docs/frontend-backend-contract.md
- ai/repo-context.md
- ai/architecture-index.md
- backend/README.md

## Expected Files to Modify
- docs/roadmap.md
- docs/decisions.md
- ai/architecture-index.md
- opcionalmente un nuevo documento técnico si encaja mejor, por ejemplo:
  - docs/discord-and-server-data-plan.md

## Constraints
- No implementar integraciones reales.
- No modificar comportamiento del frontend.
- No añadir endpoints funcionales nuevos.
- No introducir dependencias nuevas.
- No tocar base de datos.
- No hacer cambios destructivos.
- Mantener el resultado claro, útil y centrado en planificación técnica.

## Validation
- Existe una estrategia documentada para los datos futuros de Discord.
- Existe una estrategia documentada para los datos futuros de servidores.
- Se distinguen claramente fuentes posibles, riesgos y fases.
- Queda explícito qué se hará primero y qué se pospone.
- La documentación sirve como base directa para siguientes tasks técnicas.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.
