---
id: TASK-261
title: Improve current match killfeed layout for normalized weapon icons
status: done
type: frontend
team: Frontend Senior
supporting_teams: [Experto en interfaz]
roadmap_item: current-match
priority: high
---

# TASK-261 - Improve current match killfeed layout for normalized weapon icons

## Goal

Mejorar el layout del Feed de combate de partida actual para que los iconos de armas normalizados, el label del arma, los nombres de jugadores y los badges de equipo entren correctamente sin cortar filas ni desbordar.

## Context

Despues de normalizar los assets de armas y ajustar el frame visual, el problema visible ya no es solo el tamano del icono. El contenedor/card del killfeed tiene poco espacio para killer, tag de equipo, icono, label del arma, victima y tag de equipo. En produccion el feed queda visualmente apretado y algunas filas se perciben cortadas o mal proporcionadas.

Preservar la identidad HLL Vietnam: militar, Vietnam, tactica y sobria. No tocar assets ni backend.

## Steps

1. Diagnosticar el layout actual del killfeed en HTML, JS y CSS relacionados.
2. Ajustar el layout CSS para dar altura suficiente a las kill cards, columna central estable al arma y ellipsis a nombres/labels.
3. Eliminar scroll interno del feed de combate.
4. Limitar en frontend el numero de eventos renderizados para mostrar solo filas completas.
5. Mantener dos columnas solo con ancho suficiente y pasar a una columna en ancho medio/mobile.
6. Validar visualmente las vistas de partida actual para `comunidad-hispana-01` y `comunidad-hispana-02`.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `ai/orchestrator/ui-expert.md`
- `frontend/partida-actual.html`
- `frontend/assets/js/partida-actual.js`
- `frontend/assets/css/historico.css`

## Expected Files to Modify

- `frontend/assets/css/historico.css`
- `frontend/assets/js/partida-actual.js`
- `ai/tasks/done/TASK-261-improve-current-match-killfeed-layout-for-normalized-weapon-icons.md`

`frontend/assets/js/partida-actual.js` se modifica para limitar los eventos visibles por breakpoint.

## Constraints

- No ejecutar `ai-platform run`.
- No hacer commit ni push.
- No tocar backend, scheduler, RCON, TeamKills, Elo/MMR, configuracion de servidores ni el puerto 27001.
- No reintroducir Comunidad Hispana #03.
- No tocar assets fisicos de armas, SVGs, PNGs, `frontend/assets/img/weapons/`, mapas, clans ni brands.
- No tocar `ai/system-metrics.md`.
- No incluir `tmp/`, TASK-204 ni cambios previos no relacionados.
- No usar `git add .`.
- Mantener cambios pequenos, verificables y documentados.

## Validation

- Si se toca JS: `node --check frontend/assets/js/partida-actual.js`.
- Validacion visual en navegador:
  - `/partida-actual.html?server=comunidad-hispana-01`
  - `/partida-actual.html?server=comunidad-hispana-02`
- Validar con casos reales o simulados: nombres cortos, nombres largos con clan tags, rifle, MG, mina, strafing run / bombing run y arma con label largo.
- Confirmar que no se cortan filas, el ultimo elemento no queda medio oculto, el icono queda centrado, el nombre del arma no desborda, killer/victima no empujan fuera el arma, dos columnas solo aparecen con ancho suficiente y una columna aparece en ancho medio/mobile.
- No repetir la auditoria Python si sigue bloqueada por TLS de `urllib`; documentar el bloqueo si aplica.
- Revisar `git diff --name-only` y confirmar que el alcance coincide con la task.

## Outcome

Diagnostico corregido:

- El usuario no quiere scroll interno en el Feed de combate.
- El contenedor exacto de la lista es `#current-match-feed-list.current-match-killfeed`, creado en `initializeKillFeed()` dentro de `.current-match-killfeed-screen`.
- La correccion anterior quitaba cortes, pero convertia `#current-match-feed-list.current-match-killfeed` en nodo scrolleable con `max-height: 620px`, `overflow-y: auto`, `scroll-padding-bottom` y `scrollbar-gutter`.
- El comportamiento correcto es renderizar solo las bajas recientes que caben completas y ocultar eventos mas antiguos cuando hay demasiados.

Cambios aplicados:

- Se elimino el scroll interno de `.current-match-killfeed`:
  - sin `overflow-y: auto`
  - sin `scrollbar-gutter`
  - sin `scroll-padding-bottom`
  - `max-height: none`
  - `overflow: visible`
- `.current-match-killfeed-screen` se mantiene como wrapper visual con `overflow: visible`, `box-sizing: border-box` y padding `10px 10px 12px`.
- `frontend/assets/js/partida-actual.js` limita los eventos visibles antes de renderizar:
  - desktop ancho: maximo 12 kills
  - ancho medio / una columna: maximo 6 kills
  - mobile: maximo 5 kills
- Si hay mas eventos almacenados que visibles, el estado muestra: `Mostrando las últimas N bajas detectadas.`
- Se mantienen las mejoras previas: filas de `min-height: 74px`, columna de arma `128px`, mobile `104px`, ellipsis en nombres/labels y una columna desde `max-width: 1280px`.

Validacion ejecutada:

- `node --check frontend/assets/js/partida-actual.js`: OK.
- Browser plugin: no se pudo usar porque la herramienta requerida `node_repl js` no esta expuesta; se uso Playwright local como fallback.
- Fixture larga de 20 kills interceptando las APIs de la pagina real:
  - desktop `1440px`: renderiza 12 kills, 2 columnas, `overflow-y: visible`, `scrollHeight == clientHeight`, sin scrollbar interno, `clippedRows: 0`, copy `Mostrando las últimas 12 bajas detectadas.`
  - medio `1100px`: renderiza 6 kills, 1 columna, `overflow-y: visible`, `scrollHeight == clientHeight`, sin scrollbar interno, `clippedRows: 0`, copy `Mostrando las últimas 6 bajas detectadas.`
  - mobile `390px`: renderiza 5 kills, 1 columna, `overflow-y: visible`, `scrollHeight == clientHeight`, sin scrollbar interno, `clippedRows: 0`, copy `Mostrando las últimas 5 bajas detectadas.`
- Rutas reales local y publicas con Playwright:
  - `partida-actual.html?server=comunidad-hispana-01`
  - `partida-actual.html?server=comunidad-hispana-02`
  - sin errores de consola ni `TypeError`.
- Endpoints publicos `current-match-*` con PowerShell: todos respondieron `200`.
- La auditoria Python no se repitio porque sigue bloqueada por TLS de `urllib` en este entorno:
  `CERTIFICATE_VERIFY_FAILED: Basic Constraints of CA cert not marked critical`.

Alcance:

- TASK-261 queda en `ai/tasks/done` para cierre y commit aislado.
- No se tocaron assets fisicos, SVGs, PNGs, `frontend/assets/img/weapons/`, backend, scheduler, RCON, TeamKills, Elo/MMR, mapas, clans, brands, configuracion de servidores, `27001`, `ai/system-metrics.md` ni TASK-204.

## Change Budget

- Preferir menos de 5 archivos modificados.
- Preferir menos de 200 lineas cuando sea viable.
- Dividir en follow-up si el alcance crece.


