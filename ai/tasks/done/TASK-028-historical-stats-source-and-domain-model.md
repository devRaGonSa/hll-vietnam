# TASK-028-historical-stats-source-and-domain-model

## Goal
Definir la fuente real, el modelo de dominio y la estrategia técnica base para estadísticas históricas de los 2 servidores reales de la comunidad.

## Context
Ya existen páginas de scoreboard/histórico para ambos servidores de la comunidad. El siguiente paso del proyecto es construir una capa histórica propia que permita consultas y rankings agregados, por ejemplo “jugadores con más kills de la última semana” por servidor. Antes de implementar ingesta o endpoints, hay que fijar claramente qué datos se van a extraer, cómo se modelan y cómo se relacionan con cada servidor.

## Steps
1. Revisar las dos fuentes reales de histórico ya disponibles para los servidores de la comunidad.
2. Definir qué entidades de dominio hacen falta como base. Incluir al menos:
   - servidor
   - partida
   - mapa
   - modo
   - jugador
   - participación de jugador en partida
   - métricas de partida por jugador
3. Definir qué métricas históricas mínimas interesan en esta primera fase. Incluir al menos:
   - kills
   - muertes si está disponible
   - fecha/hora de partida
   - duración
   - mapa
   - servidor
4. Definir la estrategia de identidad y deduplicación:
   - cómo identificar partidas
   - cómo identificar jugadores si el scoreboard no da un id perfecto
   - cómo evitar duplicados en la ingesta
5. Definir el alcance inicial de analítica histórica. Incluir expresamente:
   - top kills de la última semana por servidor
6. Documentar riesgos y límites:
   - estructura real del scoreboard
   - disponibilidad
   - scraping/control de cambios de HTML si aplica
   - granularidad de datos
7. Actualizar la documentación técnica del repo con este modelo base.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/current-hll-servers-source-plan.md
- docs/frontend-backend-contract.md
- backend/README.md
- cualquier código ya existente sobre histórico o scoreboard
- las URLs reales de scoreboard ya usadas por la comunidad

## Expected Files to Modify
- ai/architecture-index.md
- docs/decisions.md
- opcionalmente un nuevo documento técnico, por ejemplo:
  - docs/historical-stats-domain-model.md
- opcionalmente backend/README.md si conviene reflejar el nuevo frente técnico

## Constraints
- No implementar todavía scraping/ingesta completa en esta task.
- No introducir UI histórica aún.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en fuente, dominio y estrategia técnica.
- Mantener foco en los 2 servidores reales de la comunidad.

## Validation
- Existe un modelo de dominio claro para histórico.
- Queda definida la fuente real de histórico para ambos servidores.
- Queda definida la métrica inicial prioritaria: top kills de la última semana por servidor.
- La documentación queda utilizable como base directa para las siguientes tasks.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.

## Outcome
- Se crea `docs/historical-stats-domain-model.md` como documento base para fuente real, entidades de dominio, identidad y deduplicación del histórico.
- `docs/decisions.md` fija que el histórico de scoreboards reales queda separado del estado A2S actual.
- `ai/architecture-index.md` y `backend/README.md` referencian explícitamente el nuevo frente histórico.

## Validation Result
- Verificadas las dos fuentes reales de la comunidad en `https://scoreboard.comunidadhll.es/games` y `https://scoreboard.comunidadhll.es:5443/games`.
- Verificado además que ambas cargan la misma SPA pública `Hell Let Loose Stats`, con referencias visibles a `games`, `players`, `kills`, `deaths`, `matches` y `server`.
- Revisado `git diff --name-only`.
- Resultado: el alcance documental queda limitado a `docs/historical-stats-domain-model.md`, `docs/decisions.md`, `ai/architecture-index.md` y `backend/README.md`.

## Decision Notes
- Se documenta el scoreboard como fuente real del histórico y A2S como fuente del estado live para no mezclar dominios distintos.
- La primera analítica prioritaria se fija en `top kills de la última semana por servidor` y no en un dashboard histórico genérico.
