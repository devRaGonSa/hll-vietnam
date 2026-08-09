# TASK-011-frontend-health-and-trailer-progressive-enhancement

## Goal
Realizar el primer enlace real entre frontend y backend en HLL Vietnam mediante una mejora progresiva y controlada, consultando el estado del backend y, de forma opcional, el endpoint placeholder del tráiler, sin romper la landing estática actual.

## Context
La landing actual ya funciona como página estática simple con logo, botón de Discord y tráiler embebido. El backend ya dispone de un bootstrap y de endpoints placeholder. El siguiente ajuste lógico es introducir una mejora progresiva mínima desde `frontend/assets/js/main.js`, manteniendo fallback estático cuando el backend no esté disponible.

## Steps
1. Revisar el frontend actual y el plan de consumo de datos.
2. Revisar el backend actual y el contrato frontend-backend.
3. Preparar en `main.js` una integración mínima con el backend, manteniendo la simplicidad del proyecto.
4. Consultar al menos:
   - `GET /health`
5. Evaluar si también conviene consumir:
   - `GET /api/trailer`
   siempre manteniendo fallback estático en el HTML.
6. Añadir una señal visual mínima, discreta y no intrusiva para reflejar estado del backend si la integración lo justifica.
7. Asegurar que, si el backend no está disponible, la landing sigue funcionando exactamente como página estática.
8. No introducir todavía integración real de Discord ni servidores.
9. Mantener intacta la identidad visual general de la landing.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- docs/frontend-backend-contract.md
- docs/frontend-data-consumption-plan.md
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css
- backend/app/main.py
- backend/app/routes.py
- backend/app/payloads.py

## Expected Files to Modify
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css
- opcionalmente documentación mínima si fuera necesario reflejar el comportamiento progresivo

## Constraints
- No rediseñar la landing completa.
- No añadir nuevas secciones grandes.
- No integrar Discord real.
- No integrar servidores reales.
- No añadir librerías nuevas.
- No romper el funcionamiento estático actual.
- No hacer cambios destructivos.
- Mantener la mejora contenida y reversible.

## Validation
- La landing sigue funcionando aunque el backend no esté disponible.
- El frontend puede consultar `/health` correctamente cuando el backend está levantado.
- El comportamiento visual añadido es discreto y coherente.
- El tráiler y el botón de Discord siguen funcionando.
- La solución sienta la base para consumos reales futuros sin introducir complejidad excesiva.

## Change Budget
- Preferir menos de 4 archivos modificados.
- Preferir menos de 200 líneas cambiadas.
