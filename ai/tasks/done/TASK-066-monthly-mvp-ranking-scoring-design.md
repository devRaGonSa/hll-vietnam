# TASK-066-monthly-mvp-ranking-scoring-design

## Goal
Diseñar de forma precisa y defendible la fórmula de puntuación para una V1 del ranking mensual de mejores jugadores, usando únicamente métricas ya persistidas y fiables en el proyecto.

## Context
La auditoría de datos previa ya dejó claro qué métricas están hoy disponibles con fiabilidad suficiente para una primera versión del ranking mensual. La recomendación actual para una V1 realista se basa en:
- kills
- support
- time played
- KPM derivado
- KDA derivado
- umbrales de participación
- penalización por teamkills opcional

Antes de implementar nada en backend o UI, hace falta fijar claramente:
- qué métricas entran en la fórmula
- con qué pesos
- qué requisitos mínimos de elegibilidad debe cumplir un jugador
- cómo evitar rankings absurdos por muestras demasiado pequeñas
- cómo se resuelven empates
- si la V1 se calcula por servidor, globalmente o en ambos modos

## Steps
1. Revisar la auditoría previa de datos del ranking mensual y confirmar el conjunto de métricas fiables disponibles hoy.
2. Definir qué significa exactamente “mejor jugador del mes” en la V1 del proyecto:
   - orientación más ofensiva
   - orientación más equilibrada
   - orientación más MVP de equipo
3. Diseñar una fórmula de scoring concreta para V1 basada únicamente en métricas persistidas y fiables.
4. Definir con claridad:
   - métricas incluidas
   - pesos de cada métrica
   - normalización o escala
   - tratamiento de muestras pequeñas
   - mínimos de elegibilidad
   - penalizaciones opcionales (por ejemplo teamkills)
   - desempates
5. Recomendar si la V1 debe publicarse como:
   - ranking por servidor
   - ranking global
   - ambos
6. Justificar por qué esa fórmula es razonable para una primera versión del producto.
7. Dejar expresamente fuera de V1 las métricas no suficientemente confirmadas o no persistidas hoy, por ejemplo:
   - garrisons/OPs
   - duelos directos
   - kills por arma
   - impacto táctico fino no persistido
8. Añadir, si aporta valor, una breve nota de futuro sobre cómo podría ampliarse la fórmula en una V2 sin rediseñarla por completo.
9. No implementar todavía nuevas tablas, rutas, snapshots ni UI.
10. Al completar la implementación:
    - dejar el repositorio consistente
    - hacer commit
    - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/monthly-player-ranking-data-audit.md
- docs/historical-domain-model.md
- docs/historical-data-quality-notes.md
- backend/README.md
- backend/app/historical_models.py
- backend/app/historical_storage.py
- backend/app/payloads.py

## Expected Files to Modify
- un documento nuevo, por ejemplo:
  - docs/monthly-mvp-ranking-scoring-design.md
- opcionalmente docs/decisions.md si surge una decisión técnica clara sobre alcance V1
- opcionalmente ai/architecture-index.md si conviene enlazar el diseño de scoring

## Constraints
- No implementar todavía el ranking mensual.
- No tocar producto visible.
- No depender de métricas no confirmadas o no persistidas hoy.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en diseño de scoring y reglas de elegibilidad de V1.

## Validation
- Existe un documento claro con la fórmula de scoring propuesta para la V1.
- Quedan definidos los pesos, métricas, mínimos y desempates.
- Queda claro qué se incluye en V1 y qué se deja para V2.
- La propuesta es coherente con la auditoría de datos previa.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 4 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
