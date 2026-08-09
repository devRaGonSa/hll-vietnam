# TASK-005-frontend-backend-contract

## Goal
Definir el contrato inicial entre frontend y backend para el proyecto HLL Vietnam, estableciendo endpoints, formatos de respuesta y convenciones mínimas sin implementar todavía integraciones reales con Discord, servidores de juego o base de datos.

## Context
El proyecto ya dispone de una landing mínima funcional y de un backend Python bootstrap con verificación básica de estado. Antes de añadir lógica real, es importante fijar un contrato claro entre frontend y backend para evitar improvisación posterior y permitir que futuras tasks implementen endpoints y consumo de datos de forma consistente.

## Steps
1. Revisar la estructura actual del frontend y del backend.
2. Revisar el estado actual del backend bootstrap y el endpoint de salud existente.
3. Definir el conjunto mínimo de endpoints previstos a corto plazo, aunque algunos queden documentados como futuros. Incluir al menos:
   - `GET /health`
   - `GET /api/community`
   - `GET /api/trailer`
   - `GET /api/discord`
   - `GET /api/servers`
4. Para cada endpoint, documentar:
   - propósito
   - método HTTP
   - ruta
   - formato de respuesta
   - ejemplo JSON
   - estado actual: implementado, previsto o placeholder
5. Definir convenciones básicas de respuesta:
   - nombres de campos
   - estructura JSON
   - uso de `status`
   - tratamiento mínimo de errores
6. Documentar cómo debería consumir el frontend estos endpoints más adelante, sin implementarlo todavía.
7. Añadir o actualizar documentación técnica para que el contrato quede claro dentro del repositorio.
8. Si detectas incoherencias pequeñas entre documentación y bootstrap actual, corrígelas sin salirte del alcance.

## Files to Read First
- README.md
- AGENTS.md
- docs/project-overview.md
- docs/roadmap.md
- docs/decisions.md
- ai/repo-context.md
- ai/architecture-index.md
- backend/README.md
- backend/app/__init__.py
- backend/app/main.py
- frontend/index.html
- frontend/assets/js/main.js

## Expected Files to Modify
- docs/project-overview.md
- docs/decisions.md
- backend/README.md
- ai/architecture-index.md
- opcionalmente un nuevo documento técnico si encaja mejor, por ejemplo:
  - `docs/frontend-backend-contract.md`

## Constraints
- No implementar todavía endpoints reales adicionales.
- No integrar Discord real.
- No integrar servidores de juego reales.
- No introducir base de datos.
- No cambiar el comportamiento visible del frontend.
- No añadir frameworks ni dependencias nuevas.
- No hacer cambios destructivos.
- Mantener la solución clara, pequeña y útil para futuras tasks.

## Validation
- Existe documentación clara del contrato inicial frontend-backend.
- `GET /health` queda reflejado correctamente como endpoint actual.
- Los endpoints futuros quedan documentados con ejemplos coherentes.
- El contrato usa convenciones consistentes de respuesta JSON.
- El repositorio queda preparado para que siguientes tasks implementen endpoints reales de forma ordenada.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
## Outcome

- Se aÃ±adiÃ³ `docs/frontend-backend-contract.md` como referencia central del contrato inicial frontend-backend.
- Se actualizaron `docs/project-overview.md`, `docs/decisions.md` y `backend/README.md` para reflejar el contrato y el estado actual de `GET /health`.
- No se implementaron endpoints nuevos ni se cambiÃ³ el comportamiento visible del frontend.

## Validation Result

- Verificado con `python -c "from app.main import build_health_payload; print(build_health_payload())"` en `backend/`.
- Resultado comprobado: `{'status': 'ok', 'service': 'hll-vietnam-backend', 'phase': 'bootstrap'}`.
- No aplican integration tests para este alcance documental.
