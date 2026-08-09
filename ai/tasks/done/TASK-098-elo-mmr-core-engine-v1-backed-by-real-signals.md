# TASK-098-elo-mmr-core-engine-v1-backed-by-real-signals

## Goal
Implementar una primera versión operativa del motor de MMR persistente + MonthlyRankScore mensual usando únicamente señales reales o aproximaciones justificadas por la telemetría disponible hoy.

## Context
Esta task debe apoyarse en la especificación y capabilities de la task anterior.

La implementación debe seguir el espíritu del PDF:
- validar matches
- factor de calidad Q
- OutcomeScore
- ImpactScore por rol
- DeltaMMR
- MatchScore
- MonthlyRankScore
Pero sin fingir precisión donde no existe.

## Steps
1. Implementar la validación de partida y el factor de calidad Q con las señales disponibles reales.
2. Implementar la lógica de bucket mínima viable:
   - rol principal
   - modo si está disponible
   - tramo de duración
3. Implementar los subíndices soportables hoy:
   - OutcomeScore
   - CombatIndex
   - UtilityIndex cuando haya señal
   - LeadershipIndex cuando haya señal
   - DisciplineIndex con teamkills / abandonos / AFK si la fuente real lo permite
   - ObjectiveIndex exacto o aproximado solo si está realmente soportado
4. Implementar `ImpactScore` con pesos por rol inspirados en el PDF.
5. Implementar actualización de `MMR` persistente.
6. Implementar `MatchScore` mensual.
7. Implementar agregación mensual de `MonthlyRankScore` con:
   - Confidence
   - Activity
   - Consistency
   - StrengthOfSchedule
   - PenaltyPoints
8. Marcar explícitamente en el resultado de cada cálculo:
   - qué partes se calcularon con señal exacta
   - qué partes fueron aproximadas
   - qué partes quedaron no disponibles
9. Exponer una API o endpoints internos/backend claros para consultar:
   - rating persistente del jugador
   - leaderboard mensual Elo/MMR
   - metadata de cálculo/capabilities
10. Mantener MVP V1/V2 existentes sin romperse.

## Constraints
- No vender esta V1 del motor como “idéntica al PDF” si hay aproximaciones.
- No usar valores mágicos sin documentarlos.
- No romper endpoints históricos actuales.
- No rehacer toda la UI en esta task.

## Validation
- Existe cálculo persistente de MMR para jugadores soportados.
- Existe cálculo mensual visible de ranking/score.
- El resultado expone metadata de exactitud/aproximación.
- La repo queda consistente.
- La documentación queda alineada con lo realmente implementado.

## Expected Files
- archivos backend nuevos o modificados bajo `backend/app/` para engine/storage/routes/payloads Elo
- `backend/README.md`
- `docs/elo-mmr-monthly-ranking-design.md`
