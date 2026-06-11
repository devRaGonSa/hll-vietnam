# TASK-256 - Polish player profile layout, name fallback and user copy

## Summary

This task polishes the public player profile in `stats.html` after TASK-253 and TASK-255.

Changes included:

- moved external profile links out of the lower summary grid
- kept selected search-result names as UI fallback when the profile payload has no player name
- replaced technical user-facing copy with player-friendly messages
- kept KPM visibility restricted to `kpm_status == ready`

## External Profile Layout

`Perfiles externos` now renders directly under the `Perfil personal` state text and before the weekly/monthly comparison cards.

The lower summary grid now only contains:

- `Identidad`
- `Ventana semanal`
- `Ventana mensual`

The links remain responsive and wrap on narrow screens.

## Player Name Fallback

Root cause:

- degraded weekly/monthly profile payloads can return no `player_name`
- the frontend then fell back to `Sin nombre`
- this ignored the player name already selected from search results

Fix:

- the selected result name is passed into `loadPlayerProfile(...)`
- visible name priority is:
  - payload player name if it is usable
  - selected search-result name
  - current search text if it looks like a name
  - `Jugador seleccionado`

Raw Steam/Epic identifiers are not used as visible profile names.

## User Copy

Replaced visible technical wording:

- `Backend no disponible...` -> `Servicio no disponible...`
- `Verifica backend...` -> `Intentalo de nuevo en unos segundos.`
- `Jugador sin estadisticas suficientes...` -> `Todavia no hay estadisticas suficientes para este jugador.`
- `Ranking ausente` -> `Sin posicion`
- backend/recalculation note -> `Comparativa basada en los datos disponibles actualmente.`

Internal variable names and fetch URLs still use backend terminology where required by code.

## Validation

Executed:

- `node --check frontend/assets/js/stats.js`

Static checks:

- no visible `Sin nombre` fallback remains in stats UI
- no visible profile copy mentions backend, endpoint, payload, read model, ranking block, or recalculation
- KPM is still rendered only for `kpm_status == ready`
- Steam profile links still resolve to Steam + Hellor + HLL Records + Helo
- Epic profile links still resolve to Hellor + HLL Records

## Notes

- No backend changes.
- No TeamKills changes.
- No asset changes.
- No scheduler/RCON/server configuration changes.
