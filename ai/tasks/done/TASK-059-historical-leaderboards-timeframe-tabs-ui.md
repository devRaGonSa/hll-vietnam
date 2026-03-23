# TASK-059-historical-leaderboards-timeframe-tabs-ui

## Goal
Ampliar la sección de tops de la página histórica para permitir alternar entre rankings semanales y mensuales dentro de la misma zona visual, manteniendo también las pestañas por métrica.

## Context
La sección de tops ya tiene pestañas por métrica:
- Top kills
- Top muertes
- Partidas 100+ kills
- Soporte

Ahora se quiere añadir una segunda capa de navegación temporal dentro de esa misma sección para consultar:
- semanal
- mensual

La experiencia debe seguir siendo clara, rápida y coherente con el estilo actual de la página.

## Steps
1. Revisar la UI actual de la sección de leaderboards.
2. Revisar la nueva API mensual y cómo convive con la semanal.
3. Diseñar una navegación clara para el marco temporal, por ejemplo:
   - Semanal
   - Mensual
4. Mantener las pestañas de métricas ya existentes dentro de ese marco temporal.
5. Hacer que la UI pueda alternar entre:
   - semanal + kills
   - semanal + muertes
   - semanal + 100+ kills
   - semanal + soporte
   - mensual + kills
   - mensual + muertes
   - mensual + 100+ kills
   - mensual + soporte
6. Mostrar el rango temporal real usado de forma clara y natural.
7. Mantener estados de loading, empty y error.
8. Mantener el rendimiento percibido razonable y compatible con la estrategia actual de snapshots.
9. No crear una nueva página; la ampliación debe quedar dentro de la sección actual de tops.
10. Al completar la implementación:
    - dejar el repositorio consistente
    - hacer commit
    - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- frontend/historico.html
- frontend/assets/js/historico.js
- frontend/assets/css/historico.css
- backend/app/routes.py
- backend/app/payloads.py
- backend/README.md

## Expected Files to Modify
- frontend/historico.html
- frontend/assets/js/historico.js
- frontend/assets/css/historico.css
- opcionalmente backend docs mínimas si cambia el contrato visible de uso

## Constraints
- No romper el flujo actual semanal.
- No introducir frameworks nuevos.
- No crear páginas nuevas.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en la navegación temporal dentro de los tops.

## Validation
- La sección de tops permite alternar entre semanal y mensual.
- Siguen funcionando las métricas actuales.
- El rango temporal mostrado es claro.
- La UI sigue siendo coherente con el resto de la página histórica.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados.
- Preferir menos de 220 líneas cambiadas.
