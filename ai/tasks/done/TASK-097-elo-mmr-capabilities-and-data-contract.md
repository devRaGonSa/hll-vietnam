# TASK-097-elo-mmr-capabilities-and-data-contract

## Goal
Definir e implementar la base de contrato de datos, capabilities y storage para un sistema de MMR persistente + MonthlyRankScore mensual inspirado en `sistema_elo_mensual_hll.pdf`, adaptado a la telemetría real disponible hoy.

## Context
El PDF define una arquitectura con:
- MMR persistente
- ranking mensual visible
- calidad de match
- subíndices por rol
- ImpactScore
- MatchScore
- MonthlyRankScore
Pero la repo actual no dispone de todas las métricas del documento con precisión total.

Hace falta una base sólida que no mezcle:
- lo que el PDF ideal propone
- lo que hoy se puede calcular de verdad

## Steps
1. Leer el PDF `sistema_elo_mensual_hll.pdf` y descomponerlo en:
   - inputs obligatorios
   - inputs opcionales
   - inputs no disponibles todavía
2. Auditar las fuentes reales actuales:
   - live RCON
   - read model histórico RCON
   - player-event V2
   - histórico clásico CRCON/public-scoreboard
3. Crear una especificación operativa dentro del repo para el sistema Elo/MMR:
   - qué campos existen
   - cuáles son exactos
   - cuáles son aproximados
   - cuáles no están disponibles
4. Diseñar e implementar storage mínimo para:
   - snapshots o checkpoints mensuales de rating
   - MMR persistente por jugador
   - MatchScore / impacto por match cuando proceda
   - metadata de capabilities por cálculo
5. Dejar una capa de contrato o modelos Python claros para:
   - match validity
   - quality factor Q
   - role bucket
   - subindices
   - monthly eligibility
   - penalties
6. No cerrar todavía las fórmulas finales si falta señal; primero dejar bien cerrada la base de datos y contrato semántico.

## Constraints
- No inventar métricas inexistentes.
- No mezclar cálculo final con datos no soportados.
- No romper MVP V1/V2 actuales.
- La documentación debe dejar cristalino qué parte del PDF está soportada hoy y cuál no.

## Validation
- Existe documentación técnica concreta de capabilities del sistema Elo/MMR.
- Existen modelos/contratos/backend storage listos para cálculo incremental.
- La repo deja clara la diferencia entre exacto, aproximado y no disponible.
- La repo queda consistente.

## Expected Files
- `docs/elo-mmr-monthly-ranking-design.md`
- uno o varios archivos nuevos bajo `backend/app/` para modelos/contratos/storage Elo
- `backend/README.md`
