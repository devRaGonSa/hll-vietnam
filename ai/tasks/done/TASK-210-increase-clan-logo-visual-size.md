---
id: TASK-210
title: Increase clan logo visual size
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Experto en interfaz
roadmap_item: foundation
priority: medium
---

# TASK-210 - Increase clan logo visual size

## Goal

Corregir la presencia visual de los logos de clanes en la landing publica para que ganen tamano perceptible de forma clara, con un refuerzo especifico para `BxB`, sin tocar imagenes fisicas, backend, endpoints ni logica de datos.

## Context

La seccion de clanes en `frontend/index.html` ya recibe clases especificas desde `frontend/assets/js/main.js`, incluyendo `clan-card__logo--bxb` y `clan-card--bxb`. Tambien existen reglas CSS en `frontend/assets/css/styles.css`, pero el ajuste anterior es demasiado conservador y el usuario sigue percibiendo `BxB` casi igual que antes.

El cambio debe concentrarse en el layout visual y el tratamiento CSS del contenedor/logo para aumentar la presencia de todos los clanes y dar a `BxB` un area claramente mayor, manteniendo el tono sobrio/militar del proyecto y el comportamiento responsive.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Ejecutar `git status --short --untracked-files=all` antes de modificar y confirmar que los cambios previos en `ai/system-metrics.md` y en los SVGs/assets de armas no forman parte de esta task.
2. Revisar los archivos listados en `Files to Read First`, con foco en la estructura de la seccion de clanes y en las reglas actuales de `.clan-card__logo`, `.clan-card--bxb .clan-card__brand`, `.clan-card__logo--bxb` y `.clan-card__logo--bxb img`.
3. Aumentar el tamano visual base del bloque de logo de clanes y reducir padding interno cuando limite el crecimiento real del PNG.
4. Reforzar `BxB` con una caja visual notablemente mayor que el resto, ampliando ancho/alto disponible y, si hace falta, aplicando un ajuste mas agresivo sobre `.clan-card__logo--bxb img` para compensar transparencia interna del PNG.
5. Mantener el equilibrio visual de la tarjeta para que el texto no quede aplastado ni se rompa la composicion en movil.
6. Validar por inspeccion visual, revisar `git diff --name-only`, documentar reglas cambiadas, tamanos anteriores vs nuevos y mover la task a `ai/tasks/done` al terminar.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `frontend/index.html`
- `frontend/assets/js/main.js`
- `frontend/assets/css/styles.css`
- `ai/tasks/done/TASK-207-annual-ranking-default-load-and-kpm-columns.md`

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-210-increase-clan-logo-visual-size.md`
- `frontend/assets/css/styles.css`

Optional only if strictly necessary:

- `frontend/assets/js/main.js`

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not implement backend functionality unless the task explicitly requires it.
- Do not expand Elo/MMR, historical workers or RCON server #03 handling unless the task explicitly requires it.
- Do not overwrite repository-specific context with generic platform template text.
- No ejecutar `ai-platform run`.
- No modificar `backend/`, endpoints, logica de datos ni scripts backend.
- No tocar `ai/system-metrics.md`.
- No tocar `frontend/assets/img/weapons/`, SVGs de armas ni copias relacionadas.
- No modificar imagenes fisicas de clanes ni reemplazar PNGs.
- No reactivar Elo/MMR ni reintroducir Comunidad Hispana #03.
- Mantener compatibilidad con apertura directa en navegador y comportamiento responsive.

## Validation

Before completing the task ensure:

- `git status --short --untracked-files=all` fue ejecutado antes de modificar
- se confirmo que los cambios previos en `ai/system-metrics.md` y en assets/SVGs de armas eran no relacionados y no se tocaron
- la caja visual base del logo de clanes subio aproximadamente a `150-170px` de alto visual o equivalente perceptible
- `BxB` dispone de un area notablemente mayor, aproximadamente `220-260px` de ancho disponible y `170-200px` de alto visual o equivalente perceptible
- las reglas CSS fuerzan mejor aprovechamiento del espacio disponible con `width`, `height`, `max-width`, `max-height` y `object-fit: contain` cuando convenga
- `BxB` se ve claramente mas grande que antes por inspeccion
- el resto de clanes tambien gana presencia visual por inspeccion
- el texto de las tarjetas no queda aplastado ni roto de forma fea
- responsive no rompe en movil por inspeccion
- `backend/`, scripts backend, `frontend/assets/img/weapons/` y SVGs de armas no fueron modificados
- `node --check frontend/assets/js/main.js` solo se ejecuta si se toca JS
- si solo se toca CSS, la validacion queda documentada como validacion visual
- `git diff --name-only` matches the expected scope
- no unrelated files were modified

## Outcome

Documentar:

- Reglas CSS cambiadas:
  - `.clan-card__brand`
  - `.clan-card__logo`
  - `.clan-card__logo--standard`
  - `.clan-card__logo--wide`
  - `.clan-card__logo--shield`
  - `.clan-card--bxb .clan-card__brand`
  - `.clan-card__logo--bxb`
  - `.clan-card__logo img`
  - `.clan-card__logo--wide img`
  - `.clan-card__logo--shield img`
  - `.clan-card__logo--bxb img`
- Tamano anterior vs nuevo:
  - base `.clan-card__brand`: `124-154px` a `156-176px`
  - base `.clan-card__logo`: `124px` a `160px`
  - base `img max-height`: `108px` a `144px`
  - `BxB` columna: `146-184px` a `232-268px`
  - `BxB` logo: `148px` a `204px`
  - `BxB img max-height`: `132px` a `196px`
- Tratamiento especifico de `BxB`:
  - se amplio de forma agresiva la columna visual
  - se redujo el padding interno a `4px`
  - el `img` usa `width: 100%`, `height: 100%`, `max-width: 100%`, `max-height: 196px` y `object-fit: contain` para compensar mejor el aire interno del PNG
- Validacion realizada:
  - `git status --short --untracked-files=all` ejecutado antes de cerrar la task
  - `git diff -- frontend/assets/css/styles.css` revisado antes del commit
  - validacion visual por inspeccion en desktop y movil sobre la seccion de clanes
  - confirmacion de que `BxB` gana una caja notablemente mayor y el resto de logos tambien gana presencia
  - confirmacion de que no fue necesario tocar `frontend/assets/js/main.js`
- Confirmaciones de alcance:
  - no se modificaron imagenes fisicas de clanes
  - no se tocaron `frontend/assets/img/weapons/` ni SVGs de armas
  - no se tocaron `backend/`, endpoints, logica de datos ni scripts backend
  - no se toco `ai/system-metrics.md`
  - commit aplicado: `Increase clan logo visual size`

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
