# TASK-099-elo-mmr-product-exposure-and-ui-minimal

## Goal
Exponer de forma mínima y útil en producto el nuevo sistema de rating/MMR mensual sin romper el histórico actual ni mezclarlo de forma confusa con MVP V1/V2.

## Context
Una vez exista el motor base, hace falta hacer visible el sistema:
- leaderboard mensual Elo/MMR
- score visible del mes
- rating persistente o skill score
- metadata suficiente para no confundir al usuario

## Steps
1. Auditar la UI histórica actual y decidir el punto de exposición mínimo más claro.
2. Añadir un bloque o vista mínima para:
   - rating persistente
   - score mensual
   - elegibilidad mensual
   - indicación básica de si el cálculo es exacto / aproximado / parcial
3. Mantener separación clara respecto a:
   - MVP V1
   - MVP V2
   - player-events V2
4. No saturar la UI.
5. Si procede, añadir copy/tooltip/legend breve explicando:
   - que el sistema prioriza señales reales
   - que algunas métricas avanzadas pueden estar en modo parcial según cobertura
6. Validar que los enlaces/histórico existentes no se rompen.

## Constraints
- No rehacer toda la página histórica.
- No borrar MVP V1/V2.
- No esconder la naturaleza parcial si el cálculo aún no es completo.
- Mantener UX legible y estable.

## Validation
- El sistema Elo/MMR aparece en producto de forma entendible.
- No rompe bloques existentes.
- La UI deja claro qué representa cada score.
- La repo queda consistente.

## Expected Files
- `frontend/historico.html`
- `frontend/assets/js/historico.js`
- `frontend/assets/css/historico.css`
- backend solo si hace falta ajustar payloads expuestos
