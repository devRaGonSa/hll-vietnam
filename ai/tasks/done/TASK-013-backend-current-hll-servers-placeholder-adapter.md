# TASK-013-backend-current-hll-servers-placeholder-adapter

## Goal
Preparar en el backend Python un adaptador placeholder limpio y consistente para exponer al frontend una lista provisional de servidores actuales de Hell Let Loose, sin integrar todavía una fuente externa real.

## Context
El backend ya dispone de un esqueleto API y de endpoints placeholder. Se ha decidido que la web podrá mostrar, de forma provisional, servidores actuales de Hell Let Loose mientras no existan datos reales de HLL Vietnam. Antes de conectar fuentes externas, conviene preparar un adaptador backend limpio que devuelva datos controlados con una estructura estable y preparada para sustitución futura.

## Steps
1. Revisar el backend actual, especialmente el endpoint relacionado con servidores y los payloads placeholder existentes.
2. Revisar la documentación del contrato frontend-backend y el plan de servidores actuales.
3. Definir una estructura clara y estable para el payload de servidores actuales de HLL.
4. Ajustar el backend para que `GET /api/servers` devuelva una respuesta coherente con ese modelo provisional.
5. Asegurar que el payload distinga claramente que se trata de servidores actuales de Hell Let Loose y no de HLL Vietnam, si esa distinción encaja en el modelo.
6. Mantener la implementación desacoplada para que más adelante pueda sustituirse la fuente sin romper al frontend.
7. Actualizar la documentación backend si el comportamiento real del endpoint cambia respecto a lo documentado.
8. Mantener el alcance estricto: adaptador placeholder estable, no integración real.

## Files to Read First
- AGENTS.md
- docs/frontend-backend-contract.md
- docs/discord-and-server-data-plan.md
- docs/current-hll-servers-source-plan.md
- ai/repo-context.md
- ai/architecture-index.md
- backend/README.md
- backend/app/__init__.py
- backend/app/main.py
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/config.py

## Expected Files to Modify
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/main.py
- backend/README.md
- opcionalmente documentación contractual o técnica si necesita alineación menor

## Constraints
- No integrar todavía una fuente externa real.
- No añadir scraping.
- No añadir base de datos.
- No tocar frontend en esta task.
- No introducir complejidad innecesaria.
- No hacer cambios destructivos.
- Mantener la API simple, estable y preparada para evolución posterior.

## Validation
- `GET /api/servers` devuelve un payload placeholder más consistente y útil.
- La respuesta está preparada para consumo frontend.
- La estructura deja claro que el contenido actual es provisional y basado en servidores actuales de HLL.
- La documentación backend refleja el estado real del endpoint si cambió.

## Change Budget
- Preferir menos de 5 archivos modificados.
- Preferir menos de 180 líneas cambiadas.
