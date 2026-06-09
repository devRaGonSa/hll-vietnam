---
id: TASK-206
title: Public frontend visual consistency and annual ranking layout
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Experto en interfaz
roadmap_item: foundation
priority: medium
---

# TASK-206 - Public frontend visual consistency and annual ranking layout

## Goal

Corregir la segunda pasada visual del frontend publico para unificar definitivamente las cabeceras de `index`, `historico`, `stats` y `ranking`, mejorar la legibilidad del ranking anual y ajustar la presencia visual del logo `BxB` en la seccion de clanes.

## Context

Tras `TASK-203` y la task local no commiteada `TASK-204`, el frontend publico sigue mostrando diferencias visibles entre heroes, etiquetas redundantes dentro de cabecera y un bloque anual demasiado compacto en `stats`. Esta tarea se limita a `frontend/` y a su documentacion de task: no toca backend, endpoints, logica de datos, scripts backend, snapshots, Elo/MMR pausado, Comunidad Hispana #03 ni assets/SVGs de armas.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Confirmar el estado actual del frontend publico y de la task previa local `TASK-204`.
2. Unificar el patron visual del hero tomando `index` como referencia principal y `historico` como referencia secundaria.
3. Eliminar chips o labels de pagina redundantes dentro del hero manteniendo la navegacion superior comun.
4. Rehacer solo la presentacion frontend del Top 20 anual en `stats` para separar claramente posicion, jugador y metricas.
5. Ajustar la presentacion del logo `BxB` en la seccion de clanes sin reemplazar el asset.
6. Validar por inspeccion y documentar outcome, alcance y exclusiones.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `frontend/index.html`
- `frontend/historico.html`
- `frontend/stats.html`
- `frontend/ranking.html`
- `frontend/assets/css/styles.css`
- `frontend/assets/js/stats.js`
- `frontend/assets/js/ranking.js`
- `ai/tasks/done/TASK-203-public-pages-navigation-and-copy-polish.md`

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-206-public-frontend-visual-consistency-and-annual-ranking-layout.md`
- `frontend/index.html`
- `frontend/historico.html`
- `frontend/stats.html`
- `frontend/ranking.html`
- `frontend/assets/css/styles.css`
- `frontend/assets/css/hero-header-compact.css`
- `frontend/assets/css/historico.css`
- `frontend/assets/js/stats.js`
- `frontend/assets/js/main.js`

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not implement backend functionality unless the task explicitly requires it.
- Do not expand Elo/MMR, historical workers or RCON server #03 handling unless the task explicitly requires it.
- Do not overwrite repository-specific context with generic platform template text.
- No ejecutar `ai-platform run`.
- No modificar backend, endpoints, logica de datos, generacion de snapshots ni scripts backend.
- No tocar `ai/system-metrics.md`.
- No tocar `frontend/assets/img/weapons/`, assets/SVGs de armas ni copias relacionadas.
- No reemplazar ni editar fisicamente imagenes de clanes.
- No reactivar Elo/MMR ni reintroducir Comunidad Hispana #03.

## Validation

Before completing the task ensure:

- `index.html`, `historico.html`, `stats.html` y `ranking.html` mantienen navegacion superior comun con `Inicio`, `Historico`, `Estadisticas` y `Ranking`
- los cuatro hero muestran composicion coherente con logo a la izquierda y bloque textual a la derecha
- desaparecen del hero `Historico propio`, `Seccion Stats`, `Seccion Ranking` y cualquier chip equivalente de pagina
- el logo de comunidad no cambia de tamano de forma notable entre `index`, `historico`, `stats` y `ranking`
- el copy visible mantiene `Busca un jugador por nombre o ID y revisa sus resultados semanales, mensuales y ranking anual.`
- el copy visible mantiene `Consulta los lideres publicos de la comunidad, cambia de periodo y servidor sin salir de la pagina y revisa quien destaca en cada ventana.`
- el Top 20 anual se muestra en columnas o grid legible y el `player_id` no queda pegado al nombre como dato principal
- el logo `BxB` gana presencia visual sin romper responsive
- `git diff --name-only` matches the expected scope
- no unrelated files were modified
- integration tests are run when relevant and configured

## Outcome

Archivos modificados:

- `frontend/index.html`
- `frontend/historico.html`
- `frontend/stats.html`
- `frontend/ranking.html`
- `frontend/assets/css/hero-header-compact.css`
- `frontend/assets/css/historico.css`
- `frontend/assets/css/styles.css`
- `frontend/assets/js/main.js`
- `frontend/assets/js/stats.js`
- `ai/tasks/in-progress/TASK-206-public-frontend-visual-consistency-and-annual-ranking-layout.md`

Hero unificado:

- Se marco `index`, `historico`, `stats` y `ranking` como `hero--public-page` para dejar explicita la variante publica comun.
- `hero-header-compact.css` quedo restringido a ese patron comun y `historico.css` se alineo con la misma escala de padding, gap, logo y copy.
- `historico` dejo de usar una separacion mas amplia y un logo base mas pequeno que el resto; ahora mantiene una proporcion equivalente a `index`, `stats` y `ranking`.
- `stats` y `ranking` conservan logo a la izquierda y bloque textual a la derecha con la misma composicion visual base del hero publico.

Chips eliminados del hero:

- `Historico propio`
- `Seccion Stats`
- `Seccion Ranking`

Ranking anual:

- El Top 20 anual de `stats` paso de lista compacta apilada a una tabla legible con columnas `Posicion`, `Jugador`, `Valor / Kills`, `Partidas`, `Muertes`, `Teamkills` y `K/D`.
- El `player_id` se mantiene como dato secundario visual en una segunda linea bajo el nombre, en vez de aparecer pegado al jugador.
- El bloque superior del ranking anual se suavizo con copy menos tecnico y metadatos presentados en tarjetas (`Servidor`, `Año`, `Lectura`, `Partidas base`, `Actualizado`).
- No se tocaron endpoint ni contrato API; solo se cambio la presentacion generada por `stats.js` y su CSS asociado.

Clanes / BxB:

- `BxB` recibio una variante visual especifica de tarjeta y logo (`clan-card--bxb`, `clan-card__logo--bxb`) para ganar presencia sin reemplazar la imagen ni alterar el asset original.
- El ajuste se hizo en layout y CSS, manteniendo la coherencia general de la grilla de clanes y sin romper responsive.

Textos y navegacion:

- La navegacion superior comun queda en `Inicio`, `Historico`, `Estadisticas` y `Ranking`.
- Se mantuvo el copy principal pedido en `stats` y `ranking`.
- Se corrigieron textos visibles de apoyo en `main.js` como `Historico`, `Region`, `Informacion`, `Ultimo snapshot` y `Proximamente`.

Validaciones ejecutadas:

- `git status --short --untracked-files=all` ejecutado antes de modificar.
- Confirmacion de que `TASK-204-align-public-page-heroes-and-navigation-labels.md` existe en disco pero sigue `untracked`; no estaba commiteada.
- Confirmacion previa de cambios no relacionados en `ai/system-metrics.md` y en `frontend/assets/img/weapons/` / SVGs de armas; no se tocaron.
- Lectura previa de `AGENTS.md`, `ai/repo-context.md`, `ai/architecture-index.md`, task previa relevante, HTML/CSS/JS del frontend publico y seccion de clanes.
- Revision de `git diff --name-only` para comprobar alcance restringido a frontend publico y task.
- Inspeccion visual con capturas headless de Edge sobre `frontend/index.html`, `frontend/historico.html`, `frontend/stats.html` y `frontend/ranking.html` para verificar navegacion y coherencia del hero.
- Validacion estructural de la nueva tabla anual por inspeccion del HTML/JS/CSS renderizado. La vista con datos reales no pudo comprobarse visualmente porque el backend no estaba disponible en la validacion local.

Confirmaciones de alcance:

- No se tocaron `backend/`, endpoints, logica de datos, snapshots ni scripts backend.
- No se tocaron `ai/system-metrics.md`, `frontend/assets/img/weapons/` ni los SVGs de armas con cambios previos.
- No se reactivo Elo/MMR ni se reintrodujo Comunidad Hispana #03.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
