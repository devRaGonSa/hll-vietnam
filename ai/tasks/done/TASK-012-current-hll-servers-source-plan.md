# TASK-012-current-hll-servers-source-plan

## Goal
Definir la estrategia técnica y de producto para mostrar en la web de HLL Vietnam un bloque provisional de servidores actuales de Hell Let Loose, diferenciándolos claramente del futuro contexto Vietnam y sin implementar todavía integración real definitiva.

## Context
A día de hoy el foco temático del proyecto es HLL Vietnam, pero todavía no existen servidores reales de ese entorno para consumirlos como fuente del producto. Como solución provisional y útil para la comunidad, se quiere mostrar información de servidores actuales de Hell Let Loose, dejando claro que se trata de servidores del juego actual y no de HLL Vietnam. Antes de construir integración backend o UI final, hay que documentar fuente, campos, límites y estrategia de sustitución futura.

## Steps
1. Revisar la documentación actual del proyecto y la estrategia de datos ya definida.
2. Documentar el objetivo del bloque provisional de servidores actuales de HLL.
3. Definir claramente cómo debe presentarse en producto para evitar confusión con HLL Vietnam.
4. Identificar qué campos tiene sentido mostrar en esta fase. Incluir al menos:
   - nombre del servidor
   - estado online/offline
   - jugadores actuales
   - capacidad máxima
   - mapa actual si está disponible
   - región o etiqueta útil si existe
5. Documentar las posibles fuentes de esos datos, distinguiendo entre:
   - fuente externa pública
   - datos controlados o placeholder
   - integración futura más robusta
6. Documentar riesgos y restricciones:
   - disponibilidad de terceros
   - CORS
   - rate limits
   - estabilidad del formato
   - dependencia de scraping o fuentes no oficiales
7. Proponer una estrategia por fases:
   - fase 1: payload controlado/mock con forma realista
   - fase 2: adaptador backend para fuente externa o dataset controlado
   - fase 3: sustitución por datos más cercanos a HLL Vietnam cuando existan
8. Dejar claro qué no se implementará todavía.
9. Actualizar documentación técnica del repositorio para que siguientes tasks tengan base clara.

## Files to Read First
- README.md
- AGENTS.md
- docs/project-overview.md
- docs/roadmap.md
- docs/decisions.md
- docs/frontend-backend-contract.md
- docs/discord-and-server-data-plan.md
- ai/repo-context.md
- ai/architecture-index.md
- backend/README.md

## Expected Files to Modify
- docs/roadmap.md
- docs/decisions.md
- ai/architecture-index.md
- opcionalmente un nuevo documento técnico si encaja mejor, por ejemplo:
  - docs/current-hll-servers-source-plan.md

## Constraints
- No implementar integración real todavía.
- No modificar comportamiento visible del frontend.
- No añadir dependencias nuevas.
- No tocar base de datos.
- No hacer cambios destructivos.
- Mantener el resultado centrado en planificación técnica y de producto.

## Validation
- Existe una estrategia documentada para mostrar servidores actuales de Hell Let Loose como contenido provisional.
- Queda claramente diferenciada la identidad de HLL actual frente a HLL Vietnam.
- Se documentan campos, fuentes, riesgos y fases.
- La documentación sirve como base directa para una task backend y una task frontend posteriores.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
