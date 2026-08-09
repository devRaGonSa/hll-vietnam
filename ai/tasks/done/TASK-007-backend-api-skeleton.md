# TASK-007-backend-api-skeleton

## Goal
Preparar un esqueleto inicial de API en el backend Python para HLL Vietnam, dejando rutas y estructura listas para crecimiento posterior mediante respuestas placeholder o mock, sin integrar todavía Discord ni servidores reales.

## Context
El backend ya cuenta con un bootstrap mínimo y un endpoint de salud. El contrato frontend-backend ya define un conjunto inicial de endpoints previstos. El siguiente paso técnico es convertir esa definición en una estructura API básica y mantenible, con rutas organizadas y respuestas coherentes, aunque todavía sean estáticas o placeholder.

## Steps
1. Revisar el backend actual y la documentación del contrato frontend-backend.
2. Confirmar el punto de entrada actual del backend y su estructura.
3. Preparar una organización mínima para rutas API futuras dentro de `backend/app/`.
4. Implementar o estructurar las rutas placeholder mínimas para:
   - `GET /health`
   - `GET /api/community`
   - `GET /api/trailer`
   - `GET /api/discord`
   - `GET /api/servers`
5. Hacer que las respuestas sean coherentes con el contrato ya documentado, aunque usen datos placeholder.
6. Mantener una estructura clara para crecimiento posterior, por ejemplo separando:
   - punto de entrada
   - rutas
   - utilidades o payloads placeholder si hiciera falta
7. Actualizar la documentación del backend para reflejar la nueva estructura y cómo ejecutar la API localmente.
8. Mantener el alcance estricto: esqueleto funcional, no integración real.

## Files to Read First
- AGENTS.md
- docs/frontend-backend-contract.md
- docs/project-overview.md
- docs/decisions.md
- ai/repo-context.md
- ai/architecture-index.md
- backend/README.md
- backend/requirements.txt
- backend/app/__init__.py
- backend/app/main.py

## Expected Files to Modify
- backend/app/main.py
- backend/app/__init__.py
- backend/README.md
- opcionalmente archivos nuevos dentro de `backend/app/` si mejoran claridad, por ejemplo:
  - backend/app/routes.py
  - backend/app/payloads.py

## Constraints
- No integrar Discord real.
- No integrar servidores reales.
- No añadir base de datos.
- No introducir complejidad innecesaria.
- No tocar frontend.
- No añadir frameworks nuevos si no son estrictamente necesarios para mantener coherencia con el bootstrap actual.
- No hacer cambios destructivos.
- Mantener la API simple, clara y consistente con la documentación ya existente.

## Validation
- El backend expone claramente los endpoints placeholder definidos.
- `GET /health` sigue funcionando correctamente.
- Los endpoints futuros definidos en el contrato existen al menos como placeholders coherentes.
- La estructura backend queda mejor preparada para crecimiento.
- La documentación del backend refleja el nuevo estado real.

## Change Budget
- Preferir menos de 7 archivos modificados o creados.
- Preferir menos de 260 líneas cambiadas.
