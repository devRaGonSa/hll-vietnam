---
id: TASK-212
title: Add killfeed weapon icon background
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Experto en interfaz
roadmap_item: foundation
priority: medium
---

# TASK-212 - Add killfeed weapon icon background

## Goal

Anadir una placa visual clara detras de los iconos de arma negros en la feed de bajas de `partida-actual`, sin modificar ningun SVG, asset fisico ni mapping de armas, para mejorar legibilidad dentro de la estetica militar sobria del proyecto.

## Context

En `frontend/assets/js/partida-actual.js`, la feed de bajas renderiza iconos mediante `renderKillFeedWeaponIcon()`. Actualmente esa funcion devuelve directamente un `<img class="current-match-killfeed__weapon-icon" ...>`.

Despues de `TASK-209`, `resolveKillFeedWeapon()` prioriza `globalThis.HLL_VIETNAM_CURRENT_MATCH_WEAPON_ICONS`, definido en `frontend/assets/js/current-match-weapon-icons.js`, que apunta a iconos negros desde `./assets/img/weapons/black/`. Como esos SVG tienen fondo transparente, en la feed se ve la silueta negra sin una base clara que la separe del fondo del panel.

La implementacion debe envolver el icono en un contenedor visual estable, mantener el fallback `?` dentro de la misma placa o con estilo compatible, conservar el texto del arma visible y no alterar la fila de forma exagerada ni romper responsive.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Revisar los archivos listados en `Files to Read First`, confirmando como se resuelve el icono, donde se renderiza el arma y donde viven los estilos reales del kill feed.
2. Modificar `renderKillFeedWeaponIcon()` para envolver el icono en un contenedor especifico, por ejemplo `current-match-killfeed__weapon-icon-frame`.
3. Mantener el fallback `?` dentro de la misma placa o con un estilo visual equivalente, sin cambiar el mapping de armas.
4. Anadir o ajustar CSS para dar al contenedor:
   - fondo blanco o crema militar claro
   - borde sutil
   - `border-radius`
   - `padding`
   - tamano estable
   - `display: grid` y `place-items: center`
5. Mantener el `<img>` con `object-fit: contain` y sin deformacion.
6. Validar sintaxis JS, revisar visualmente `partida-actual` en local y documentar exclusiones.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `frontend/partida-actual.html`
- `frontend/assets/js/partida-actual.js`
- `frontend/assets/js/current-match-weapon-icons.js`
- `frontend/assets/css/historico.css`

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-212-add-killfeed-weapon-icon-background.md`
- `frontend/assets/js/partida-actual.js`
- `frontend/assets/css/historico.css`

Optional only if strictly necessary:

- `frontend/partida-actual.html`
- `frontend/assets/css/styles.css`

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not overwrite repository-specific context with generic platform template text.
- No ejecutar `ai-platform run`.
- No tocar `backend/` ni endpoints.
- No tocar `frontend/assets/img/weapons/`.
- No tocar SVGs.
- No modificar imagenes fisicas.
- No cambiar el mapping de armas.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- Mantener compatibilidad con apertura directa en navegador y responsive.

## Validation

Before completing the task ensure:

- `renderKillFeedWeaponIcon()` envuelve el icono en un contenedor visual claro y estable
- los iconos negros se ven sobre una caja clara/blanca integrada con la estetica militar de la feed
- el fallback `?` usa la misma placa o un estilo compatible
- el `<img>` mantiene `object-fit: contain` y no se deforma
- la fila del kill feed no crece de forma exagerada
- el texto del arma sigue visible
- se ejecuta:

```bash
node --check frontend/assets/js/partida-actual.js
node --check frontend/assets/js/current-match-weapon-icons.js
```

- se realiza inspeccion visual local de `partida-actual`
- se confirma que no se tocaron:
  - `backend/`
  - `frontend/assets/img/weapons/`
  - SVGs
  - `ai/system-metrics.md`
- `git diff --name-only` matches the expected scope
- no unrelated files were modified

## Outcome

Documentar:

- que cambio se hizo en `renderKillFeedWeaponIcon()`
- que clases CSS nuevas o ajustadas se anadieron para la placa del icono
- como queda tratado el fallback `?`
- validacion sintactica y visual realizada
- confirmacion explicita de que no se tocaron backend, assets de armas, SVGs, imagenes fisicas, Elo/MMR ni Comunidad Hispana #03

Result:

- Updated `frontend/assets/js/partida-actual.js` so `renderKillFeedWeaponIcon()` now wraps both the `<img>` and the `?` fallback inside `current-match-killfeed__weapon-icon-frame`.
- Updated `frontend/assets/css/historico.css` with a stable light cream weapon plate and adjusted icon/fallback sizing so black transparent SVGs remain readable without changing the weapon mapping.
- Kept the weapon label visible below the icon plate and preserved the current kill feed structure and responsive behavior.

Validation performed:

- PASS: `node --check frontend/assets/js/partida-actual.js`
- PASS: `node --check frontend/assets/js/current-match-weapon-icons.js`
- PASS: visual local inspection using temporary headless-browser screenshots for desktop and mobile widths confirmed:
  - black weapon icon visible over a light plate
  - fallback `?` rendered inside the same plate
  - weapon text still visible
  - no exaggerated row growth
  - responsive layout remained usable
- PASS: reviewed `git status --short --untracked-files=all`
- PASS: reviewed `git diff --name-only`

Scope confirmation:

- No backend file or endpoint was touched.
- No weapon asset, SVG or physical image was modified.
- No weapon mapping or icon path was changed.
- `ai/system-metrics.md` was not touched by this task.
- Elo/MMR was not reactivated.
- Comunidad Hispana #03 was not reintroduced.
- No push was made.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
