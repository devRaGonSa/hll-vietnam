# TASK-010-backend-local-dev-config-and-cors-bootstrap

## Goal
Preparar la configuración mínima de desarrollo local del backend para HLL Vietnam, incluyendo parámetros básicos de ejecución y soporte controlado para consumo desde frontend local durante la fase de desarrollo.

## Context
El proyecto ya tiene frontend estático y backend placeholder. El siguiente paso para permitir un primer enlace real entre ambos es dejar clara la forma de ejecución local y, si aplica, habilitar el mínimo soporte técnico necesario para consultas desde frontend local, evitando problemas básicos de entorno o de origen cruzado en desarrollo.

## Steps
1. Revisar cómo se ejecuta actualmente el backend.
2. Definir y documentar claramente:
   - host por defecto
   - puerto por defecto
   - comando de arranque local
3. Revisar si el frontend local necesitará consumir el backend desde distinto origen durante desarrollo.
4. Si hace falta, añadir una solución mínima y controlada para CORS o para origen local de desarrollo, sin sobredimensionar el sistema.
5. Mantener la configuración simple y enfocada al entorno local.
6. Actualizar la documentación relevante para que levantar el stack local sea fácil.
7. No introducir complejidad de producción en esta fase.

## Files to Read First
- README.md
- AGENTS.md
- ai/repo-context.md
- docs/project-overview.md
- docs/frontend-backend-contract.md
- backend/README.md
- backend/app/main.py
- backend/app/routes.py

## Expected Files to Modify
- backend/README.md
- backend/app/main.py
- opcionalmente un archivo nuevo de configuración mínima si mejora claridad, por ejemplo:
  - backend/app/config.py
- opcionalmente documentación raíz si conviene reflejar arranque local combinado

## Constraints
- No integrar Discord real.
- No integrar servidores reales.
- No añadir base de datos.
- No añadir frameworks nuevos salvo que sean estrictamente necesarios y coherentes con la base ya existente.
- No tocar el comportamiento visible del frontend todavía.
- No hacer cambios destructivos.
- Mantener la configuración pequeña, clara y orientada a desarrollo local.

## Validation
- El backend tiene host/puerto local claramente definidos o documentados.
- Existe una forma clara de levantarlo en local.
- Si el frontend necesita consultar el backend desde otro origen, la solución mínima está resuelta o documentada.
- El proyecto queda listo para un primer consumo real desde frontend en una task posterior inmediata.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 180 líneas cambiadas.
