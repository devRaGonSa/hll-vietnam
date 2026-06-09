---
id: TASK-203
title: Public pages navigation and copy polish
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Experto en interfaz
roadmap_item: foundation
priority: medium
---

# TASK-203 - Public pages navigation and copy polish

## Goal

Reorganizar la navegacion superior y normalizar el layout visual de `index`, `historico`, `stats` y `ranking` para que compartan una navegacion publica coherente, una cabecera visual alineada y textos visibles corregidos en UTF-8.

## Context

Las paginas publicas principales ya exponen el producto, pero hoy mezclan botones sueltos dentro del hero, encabezados desalineados y varios textos mal codificados o demasiado tecnicos para usuarios normales. Esta tarea corrige solo la capa visual y de copy en `frontend/`, sin tocar backend, endpoints, logica de datos, Elo/MMR pausado, Comunidad Hispana #03 ni assets/SVGs de armas.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Inspeccionar el HTML, CSS y JS compartidos de las paginas publicas afectadas.
2. Crear o reutilizar una navegacion superior global para `index`, `historico`, `stats` y `ranking`.
3. Alinear el hero de `stats` y `ranking` con la composicion visual usada por `index` y `historico`.
4. Limpiar botones duplicados dentro del hero y simplificar el copy visible sin cambiar logica de datos.
5. Corregir textos visibles con problemas de codificacion en las paginas afectadas y validar el resultado por inspeccion.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `frontend/index.html`
- `frontend/historico.html`
- `frontend/assets/css/styles.css`

## Expected Files to Modify

- `ai/tasks/done/TASK-203-public-pages-navigation-and-copy-polish.md`
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
- No modificar `backend/`, scripts de validacion backend, endpoints, logica de datos, assets/SVGs de armas ni siluetas.
- No reactivar Elo/MMR ni reintroducir Comunidad Hispana #03.

## Validation

Before completing the task ensure:

- `index.html`, `historico.html`, `stats.html` y `ranking.html` muestran navegacion superior con acceso a Inicio, Historico, Stats y Ranking
- `index.html` mantiene `Unirse al Discord` dentro del hero
- `stats.html` y `ranking.html` muestran imagen/icono de comunidad en hero
- `stats.html` y `ranking.html` ya no muestran `Backend operativo`
- no aparecen textos mal codificados visibles como `PÃƒÂºblico`, `PÃƒÂºblicos`, `AÃƒÂ±o`, `AÃƒo`, `HistÃƒÂ³rico`
- `ranking.html` ya no muestra `Fuente` en el panel visible de tabla activa
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
- `ai/tasks/done/TASK-203-public-pages-navigation-and-copy-polish.md`

Navegacion nueva:

- Se anadio una navegacion superior comun en las cuatro paginas publicas con acceso directo a Inicio, Historico, Stats y Ranking.
- El estado activo se marca por pagina y la navegacion queda separada del hero como banda superior de tabs tacticos.

Textos corregidos:

- Se corrigieron textos visibles relacionados con Historico, publico/publicos, estadisticas, metrica, limite y ano/anual.
- En HTML se usaron entidades para asegurar render correcto en entorno Windows y lectura segura en navegador.
- En JS visible se usaron escapes Unicode donde hacia falta para evitar mojibake.

Botones movidos:

- En `index`, `Stats`, `Ranking` y `Ver historico propio` salieron del hero y pasaron a la navegacion global.
- En `historico`, `Volver inicio` y `Stats` se sustituyeron por la navegacion global, y se anadio acceso directo a Ranking.
- En `stats` y `ranking`, los enlaces de retorno cruzado del hero se sustituyeron por la navegacion global.

Elementos retirados:

- Se elimino el badge visible de backend en `stats` y `ranking`.
- Se elimino el campo visual `Fuente` del panel visible de metadata en `ranking`.

Validaciones ejecutadas:

- Revision por inspeccion de `frontend/index.html`, `frontend/historico.html`, `frontend/stats.html` y `frontend/ranking.html`.
- Verificacion de navegacion superior comun en las cuatro paginas.
- Verificacion de que `Unirse al Discord` permanece en el hero de `index`.
- Verificacion de que `stats` y `ranking` incluyen `logo.png` en el hero.
- Verificacion de que ya no existen `id="stats-backend-state"` ni `id="ranking-backend-state"` en HTML.
- Verificacion de que `ranking.js` ya no genera la tarjeta visible `Fuente`.
- Revision de `git status --short --untracked-files=all` y `git diff --name-only`.
- Confirmacion de que no hay cambios en `backend/` ni en `scripts/`.

Tests:

- No se ejecutaron scripts de validacion frontend existentes porque los scripts disponibles no son ligeros para este alcance y uno de ellos (`scripts/run-stats-validation.ps1`) exige el chip `stats-backend-state`, eliminado intencionadamente por esta task. No se modifico ese script por estar fuera de alcance.

Confirmaciones de alcance:

- No se tocaron `backend/`, endpoints, logica de datos, scripts backend, Elo/MMR ni Comunidad Hispana #03.
- No se tocaron assets/SVGs de armas. Los cambios ya presentes en `frontend/assets/img/weapons/` y `ai/system-metrics.md` eran previos y se dejaron intactos.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.

