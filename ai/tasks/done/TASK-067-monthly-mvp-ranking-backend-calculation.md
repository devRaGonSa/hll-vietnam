# TASK-067-monthly-mvp-ranking-backend-calculation

## Goal
Implementar en backend el cálculo base de la V1 del ranking mensual MVP usando la fórmula y reglas definidas en docs/monthly-mvp-ranking-scoring-design.md, apoyándose únicamente en métricas ya persistidas y fiables.

## Context
La auditoría y el diseño de scoring ya están cerrados. La V1 del ranking mensual MVP debe construirse con:
- kills
- support
- time played
- KPM derivado
- KDA derivado
- umbrales de elegibilidad
- penalización por teamkills opcional
- desempates deterministas

Antes de exponerlo en snapshots o UI, hace falta implementar el cálculo mensual real en backend de forma clara, trazable y compatible con servidor individual y all-servers.

## Steps
1. Revisar docs/monthly-player-ranking-data-audit.md y docs/monthly-mvp-ranking-scoring-design.md.
2. Implementar la lógica de cálculo del ranking mensual MVP según la fórmula aprobada.
3. Aplicar correctamente:
   - métricas incluidas
   - pesos
   - normalización
   - mínimos de elegibilidad
   - penalización por teamkills si así quedó definida
   - desempates
4. Soportar cálculo para:
   - un servidor concreto
   - all-servers
5. Dejar el resultado estructurado para poder serializarlo después en snapshots o payloads.
6. Mantener clara la separación entre:
   - ranking mensual MVP V1
   - leaderboards mensuales simples por métrica ya existentes
7. No exponer todavía UI nueva en esta task.
8. Documentar brevemente la parte backend necesaria.
9. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- docs/monthly-player-ranking-data-audit.md
- docs/monthly-mvp-ranking-scoring-design.md
- backend/README.md
- backend/app/historical_storage.py
- backend/app/historical_models.py
- backend/app/payloads.py
- backend/app/routes.py
- backend/app/historical_snapshots.py

## Expected Files to Modify
- backend/app/historical_storage.py
- backend/app/payloads.py
- opcionalmente nuevos módulos si mejoran claridad, por ejemplo:
  - backend/app/monthly_mvp.py
  - backend/app/monthly_mvp_scoring.py
- backend/README.md
- opcionalmente docs/decisions.md si hace falta fijar una decisión técnica menor

## Constraints
- No incluir métricas no persistidas o no confirmadas.
- No romper los rankings mensuales ya existentes por kills, muertes, soporte y 100+ kills.
- No crear todavía UI en esta task.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en el cálculo backend del monthly MVP V1.

## Validation
- Existe un cálculo mensual MVP funcional en backend.
- Soporta servidor individual y all-servers.
- Respeta la fórmula y elegibilidad definidas en el diseño.
- No rompe los leaderboards mensuales existentes.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 260 líneas cambiadas.
