---
id: TASK-204
title: Align public page heroes and navigation labels
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Experto en interfaz
roadmap_item: foundation
priority: medium
---

# TASK-204 - Align public page heroes and navigation labels

## Goal

Alinear la cabecera publica y la navegacion superior de `index`, `historico`, `stats` y `ranking` para que compartan el mismo componente visual de hero, manteniendo intacta la logica actual y el alcance frontend estatico.

## Context

Despues de `TASK-203`, `stats` y `ranking` mantenian una variante de cabecera distinta de `index` e `historico`, con logo visualmente mas pequeno, texto demasiado pegado y labels redundantes dentro del hero. Esta tarea normaliza la composicion publica reutilizando el hero de `index` como referencia visual, renombra el tab `Stats` a `Estadisticas` y corrige textos visibles con codificacion rota en las paginas afectadas.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Inspeccionar la estructura HTML/CSS actual de `index`, `historico`, `stats` y `ranking`.
2. Ajustar `stats` y `ranking` para que reutilicen la misma composicion visual de hero usada como referencia por `index` e `historico`.
3. Unificar el tamano y comportamiento visual del logo comunitario entre las cuatro paginas.
4. Eliminar labels de seccion redundantes dentro del hero y renombrar el tab `Stats` a `Estadisticas` en la navegacion publica comun.
5. Corregir textos visibles y entidades UTF-8 afectadas sin tocar backend, endpoints ni logica de datos.
6. Validar por inspeccion HTML/CSS/JS el alcance exacto y documentar el resultado.

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

- `ai/tasks/done/TASK-204-align-public-page-heroes-and-navigation-labels.md`
- `frontend/index.html`
- `frontend/historico.html`
- `frontend/stats.html`
- `frontend/ranking.html`
- `frontend/assets/css/styles.css`
- `frontend/assets/js/stats.js`
- `frontend/assets/js/ranking.js`

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not implement backend functionality unless the task explicitly requires it.
- Do not expand Elo/MMR, historical workers or RCON server #03 handling unless the task explicitly requires it.
- Do not overwrite repository-specific context with generic platform template text.
- No ejecutar `ai-platform run`.
- No modificar `backend/`, endpoints, logica de datos, scripts backend ni workers.
- No tocar `frontend/assets/img/weapons/`, assets/SVGs de armas ni las modificaciones previas detectadas en `ai/system-metrics.md`.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- No arreglar la logica o la carga de ranking anual; solo preservar la interfaz visible del area.

## Validation

Before completing the task ensure:

- `index.html`, `historico.html`, `stats.html` y `ranking.html` muestran navegacion superior comun con `Inicio`, `Historico`, `Estadisticas` y `Ranking`
- `index.html` mantiene `Unirse al Discord` dentro del hero
- `historico.html` mantiene sus filtros `Todos`, `Comunidad Hispana #01` y `Comunidad Hispana #02` en contenido
- `stats.html` y `ranking.html` usan una cabecera visual equivalente a `index` e `historico`
- desaparecen del hero `Historico propio`, `Seccion Stats`, `Seccion Ranking` y cualquier label equivalente de seccion
- no aparecen `Backend operativo` ni badges visuales equivalentes en `stats` y `ranking`
- los textos visibles muestran correctamente `Año`, `publicos`, `Historico` y `Seccion` donde corresponda
- `git diff --name-only` matches the expected scope
- no unrelated files were modified
- integration tests are run when relevant and configured

## Outcome

Archivos modificados:

- `frontend/index.html`
- `frontend/historico.html`
- `frontend/stats.html`
- `frontend/ranking.html`
- `frontend/assets/css/styles.css`
- `frontend/assets/js/stats.js`
- `frontend/assets/js/ranking.js`
- `ai/tasks/done/TASK-204-align-public-page-heroes-and-navigation-labels.md`

Clases y componentes CSS reutilizados o ajustados:

- `public-nav` y `public-nav__link` se mantuvieron como navegacion comun, con ajuste de espaciado para soportar `Estadisticas`.
- `hero-header-compact.css` se reutilizo en `stats` y `ranking` para compartir la misma escala de logo, separacion y composicion del hero de `index`.
- `logo-frame` y `logo-frame__image` se mantuvieron como base comun del componente visual del logo.

Labels eliminados:

- `Historico propio`
- `Seccion Stats`
- `Seccion Ranking`

Navegacion renombrada:

- `Stats` paso a `Estadisticas` en `index`, `historico`, `stats` y `ranking`.

Validaciones realizadas:

- Inspeccion manual de `frontend/index.html`, `frontend/historico.html`, `frontend/stats.html` y `frontend/ranking.html`.
- Confirmacion de navegacion superior comun con `Inicio`, `Historico`, `Estadisticas` y `Ranking`.
- Confirmacion de que `index` mantiene `Unirse al Discord` en el hero.
- Confirmacion de que `historico` mantiene los filtros `Todos`, `Comunidad Hispana #01` y `Comunidad Hispana #02` en su zona de contenido.
- Confirmacion de que `stats` y `ranking` cargan `hero-header-compact.css` y ya no usan una cabecera visual distinta.
- Confirmacion de que no aparecen `Backend operativo`, `Seccion Stats`, `Seccion Ranking` ni `Historico propio` en el hero publico.
- Revision de `git diff --name-only` para verificar que el alcance queda en frontend publico y la task.

Cambios de texto visibles:

- Se mantuvo `Estadisticas Personales` como titulo de `stats`.
- Se mantuvo `Ranking Global` como titulo de `ranking`.
- `Año` se conserva correctamente donde corresponde en `stats` y `ranking`.
- `publicos` se mantiene visible con tilde correcta en `ranking` mediante entidades HTML ya presentes.

Confirmaciones de alcance:

- No se toco `backend/`.
- No se tocaron endpoints ni logica de datos.
- No se toco la funcionalidad de ranking anual.
- No se tocaron scripts backend.
- No se tocaron `frontend/assets/img/weapons/` ni SVGs de armas; los cambios previos detectados alli y en `ai/system-metrics.md` se dejaron intactos.

Tests:

- No se ejecutaron tests automatizados ni `ai-platform run`; este alcance se valido por inspeccion de HTML, CSS, JS y diff, sin configuracion de test frontend especifica para esta capa visual.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
