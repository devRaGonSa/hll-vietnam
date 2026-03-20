# TASK-027-map-name-normalization-and-full-display

## Goal
Corregir la visualización del nombre de mapa en el panel actual de servidores para que se muestre correctamente, normalizado y completo, sin cortes ni etiquetas degradadas.

## Context
La landing ya muestra el estado actual de los 2 servidores reales de la comunidad, pero el campo de mapa presenta defectos visibles: nombres incompletos, abreviados de forma incorrecta o mal normalizados. Antes de avanzar con histórico y estadísticas, hay que dejar correcto este dato básico del estado actual.

## Steps
1. Revisar el origen actual del nombre de mapa en backend y frontend.
2. Identificar si el problema viene de:
   - dato crudo del query A2S
   - normalización backend
   - truncado o layout frontend
3. Corregir la cadena de transformación para que el nombre del mapa mostrado sea correcto y completo.
4. Aplicar una normalización coherente si el dato crudo usa nombres internos o variantes técnicas.
5. Asegurar que el frontend no corte el nombre de mapa de forma incorrecta.
6. Ajustar el layout si hace falta para que el mapa pueda verse entero dentro de la card.
7. Mantener los 2 servidores reales de la comunidad y no alterar el resto del flujo.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- frontend/index.html
- frontend/assets/css/styles.css
- frontend/assets/js/main.js
- backend/app/payloads.py
- backend/app/routes.py
- cualquier módulo de normalización o consulta de servidor existente
- docs/frontend-backend-contract.md

## Expected Files to Modify
- backend/app/payloads.py
- frontend/assets/js/main.js
- frontend/assets/css/styles.css
- opcionalmente frontend/index.html si el layout necesita un ajuste menor

## Constraints
- No introducir servidores ficticios.
- No romper polling ni snapshot actual.
- No añadir librerías nuevas.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en exactitud del dato y presentación correcta del mapa.

## Validation
- El nombre del mapa se muestra correctamente.
- El nombre del mapa se muestra completo.
- No aparecen abreviaturas degradadas o cortes visuales incorrectos.
- La landing mantiene su funcionamiento actual.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 4 archivos modificados.
- Preferir menos de 160 líneas cambiadas.

## Outcome
- `backend/app/normalizers.py` incorpora una normalización pequeña de nombres de mapa para convertir alias técnicos o abreviados estables de HLL en nombres legibles para la landing.
- `backend/app/payloads.py` reaplica esa normalización al leer snapshots persistidos, de modo que también se corrigen datos ya capturados como `StMarie` o `DEV_Q`.
- `frontend/assets/js/main.js` marca el valor del quickfact de mapa con una clase dedicada.
- `frontend/assets/css/styles.css` ajusta el wrapping del nombre de mapa para evitar cortes visuales degradados dentro de la card.

## Validation Result
- Ejecutado desde `backend/`: `python -` importando `build_servers_payload()`.
- Resultado: `comunidad-hispana-01 => Developer Test Map` y `comunidad-hispana-02 => Sainte-Marie-du-Mont` en el payload devuelto por `/api/servers`.
- Ejecutado desde raíz: `node --check frontend/assets/js/main.js`.
- Resultado: validación de sintaxis correcta para el script frontend.
- Revisado `git diff --name-only`.
- Resultado: el alcance queda limitado a `backend/app/normalizers.py`, `backend/app/payloads.py`, `frontend/assets/js/main.js` y `frontend/assets/css/styles.css`.

## Decision Notes
- La corrección principal se aplica en backend para mantener un único punto de verdad entre snapshots nuevos y persistidos.
- El ajuste visual en frontend se limita al campo de mapa para no alterar el layout general de la landing.
