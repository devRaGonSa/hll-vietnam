# TASK-058-monthly-historical-leaderboards-api

## Goal
Ampliar la API histórica de leaderboards para soportar una dimensión mensual además de la semanal, reutilizando las mismas métricas actuales del producto.

## Context
La página histórica ya muestra tops semanales por métrica:
- kills
- muertes
- partidas con más de 100 kills
- soporte

Ahora se quiere añadir una segunda dimensión temporal: mensual. La API debe poder servir snapshots o payloads equivalentes para el periodo mensual con la misma claridad que ya existe en semanal.

## Steps
1. Revisar la implementación actual de tops semanales y su semántica temporal.
2. Diseñar una dimensión mensual coherente para leaderboards históricos.
3. Definir la política temporal mensual, idealmente basada en mes natural cerrado o en el mes actual si la política del proyecto lo requiere, dejándolo claro.
4. Implementar soporte backend para leaderboards mensuales con estas métricas:
   - kills
   - muertes
   - partidas con más de 100 kills
   - soporte
5. Asegurar que la API exponga metadatos claros del rango temporal real usado.
6. Integrar el soporte mensual en la capa de snapshots JSON en disco.
7. Mantener compatibilidad con la capa semanal existente.
8. Documentar la nueva capacidad en backend.
9. No crear todavía la pestaña visual en esta task si no es imprescindible.
10. Al completar la implementación:
    - dejar el repositorio consistente
    - hacer commit
    - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/payloads.py
- backend/app/routes.py
- backend/app/historical_storage.py
- backend/app/historical_snapshots.py
- backend/app/historical_snapshot_storage.py
- frontend/assets/js/historico.js

## Expected Files to Modify
- backend/app/payloads.py
- backend/app/routes.py
- backend/app/historical_storage.py
- backend/app/historical_snapshots.py
- backend/app/historical_snapshot_storage.py
- backend/README.md
- opcionalmente documentación técnica adicional si hace falta aclarar la política mensual

## Constraints
- No romper tops semanales existentes.
- No usar A2S para estos tops históricos.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en leaderboards mensuales y metadatos temporales claros.

## Validation
- Existen leaderboards mensuales para las métricas soportadas.
- La API distingue correctamente entre semanal y mensual.
- Los snapshots mensuales se generan y persisten correctamente.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.
