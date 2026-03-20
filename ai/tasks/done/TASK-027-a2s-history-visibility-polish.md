# TASK-027-a2s-history-visibility-polish

## Goal
Ajustar la capa de visualización actual para que la web pueda distinguir de forma clara cuándo muestra datos históricos procedentes de snapshots A2S reales frente a placeholders o fallbacks estáticos.

## Context
Una vez que la captura A2S real esté operativa, conviene hacer visible en frontend la procedencia efectiva de los datos sin convertir la landing en un dashboard complejo. Esta task debe mejorar la claridad del bloque actual de servidores y estadísticas sin rediseñarlo completamente.

## Steps
1. Revisar el frontend actual y el bloque de estadísticas/servidores existente.
2. Revisar el formato real de los endpoints históricos tras la integración A2S.
3. Añadir una mejora visual o de estado que permita reflejar claramente si los datos mostrados son:
   - snapshots reales recientes
   - datos persistidos antiguos
   - fallback estático
4. Mantener la mejora discreta y coherente con la landing actual.
5. No convertir la página en una aplicación compleja ni añadir navegación nueva.
6. Preservar el fallback si el backend no está disponible.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- docs/frontend-data-consumption-plan.md
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css
- backend/app/routes.py
- backend/app/payloads.py

## Expected Files to Modify
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css

## Constraints
- No rediseñar toda la landing.
- No añadir librerías nuevas.
- No tocar backend salvo referencias documentales mínimas si hicieran falta.
- No hacer cambios destructivos.
- Mantener la mejora contenida y alineada con la fase actual.

## Validation
- La web distingue visualmente entre datos reales A2S, históricos persistidos y fallback estático cuando aplique.
- La integración visual sigue siendo coherente con la landing.
- El frontend sigue funcionando si el backend no responde.

## Change Budget
- Preferir menos de 4 archivos modificados.
- Preferir menos de 180 líneas cambiadas.

## Outcome
- `frontend/index.html` incorpora un bloque pequeno de procedencia para explicar si el panel muestra fallback estatico, historico persistido o snapshots A2S recientes.
- `frontend/assets/js/main.js` clasifica el estado visible segun la procedencia y la antiguedad de los snapshots historicos sin romper el fallback actual.
- `frontend/assets/css/styles.css` integra esos estados con una presentacion tactica discreta dentro del panel existente de servidores.

## Validation Result
- Ejecutado: `node --check frontend/assets/js/main.js`
- Resultado: sintaxis valida en el script principal del frontend.

## Decision Notes
- La distincion entre `snapshots A2S recientes` y `historico persistido` se resuelve de forma ligera usando `source_name` y la antiguedad de `captured_at`, evitando cambios de contrato backend en esta fase.
