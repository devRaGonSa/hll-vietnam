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
2. Ajustar el layout CSS para dar altura suficiente a las kill cards, columna central estable al arma, ellipsis a nombres/labels y scroll vertical sin cortes.
3. Mantener dos columnas solo con ancho suficiente y pasar a una columna en ancho medio/mobile.
4. Validar visualmente las vistas de partida actual para `comunidad-hispana-01` y `comunidad-hispana-02`.
5. Ejecutar la auditoria publica indicada y documentar resultado.

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
- `ai/tasks/done/TASK-261-improve-current-match-killfeed-layout-for-normalized-weapon-icons.md`

`frontend/assets/js/partida-actual.js` solo debe modificarse si hace falta anadir clases semanticas o corregir estructura.

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
- Ejecutar:
  `python .\scripts\audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --output tmp\task261_full_audit_after.json`
- Criterio minimo: CRITICAL 0, `current-match-*` OK 200 y consola sin TypeError.
- Revisar `git diff --name-only` y confirmar que el alcance coincide con la task.

## Outcome

Diagnostico corregido:

- El problema principal no era solo el ancho de cada kill card. El recorte visible venia del contenedor interno que muestra la lista de acciones/kills.
- El contenedor exacto de la lista es `#current-match-feed-list.current-match-killfeed`, creado en `initializeKillFeed()` dentro de `.current-match-killfeed-screen`.
- Antes de la correccion inicial, habia doble recorte vertical:
  - `.current-match-killfeed-screen`: `max-height: 520px` y `overflow: hidden`.
  - `.current-match-killfeed`: `max-height: 500px` y `overflow: hidden`.
- Ese doble overflow podia dejar kills partidas por la mitad en la parte inferior: el wrapper con borde recortaba y la lista interna no tenia scroll vertical util.
- Tras aumentar la altura de fila a `74px`, el viewport de lista debia crecer tambien; con muchas kills, el listado necesitaba scroll claro, padding inferior y comprobacion del ultimo item scrolleado.

Cambios aplicados:

- `.current-match-killfeed-screen` queda como wrapper visual con borde, `overflow: visible`, `box-sizing: border-box` y padding `10px 10px 12px`; no es el nodo scrolleable.
- `.current-match-killfeed` queda como unico contenedor scrolleable de la lista:
  - `max-height: 620px`
  - `overflow-y: auto`
  - `overflow-x: hidden`
  - `padding-bottom: 12px`
  - `scroll-padding-bottom: 12px`
  - `scrollbar-gutter: stable`
- Se mantienen las mejoras previas: filas de `min-height: 74px`, columna de arma `128px`, mobile `104px`, ellipsis en nombres/labels y una columna desde `max-width: 1280px`.

Validacion ejecutada:

- No se ejecuto `node --check frontend/assets/js/partida-actual.js` porque no se modifico JS.
- Validacion visual local con servidor estatico en `http://127.0.0.1:4173`:
  - `/partida-actual.html?server=comunidad-hispana-01`
  - `/partida-actual.html?server=comunidad-hispana-02`
- Fixture simulada larga fuera del repo con 20 kills, nombres largos, clan tags, rifle, MG, mina, strafing run, bombing run y labels largos.
- Medicion DOM con Playwright scrolleando la lista hasta el final:
  - desktop `1440px`: 2 columnas, `max-height: 620px`, `clientHeight: 620`, `scrollHeight: 828`, ultimo item completo.
  - medio `1100px`: 1 columna, `max-height: 620px`, `clientHeight: 620`, `scrollHeight: 1652`, ultimo item completo.
  - mobile `390px`: 1 columna, `max-height: 620px`, `clientHeight: 620`, `scrollHeight: 1648`, ultimo item completo.
  - En los tres anchos: `lastBottom <= visibleBottom - paddingBottom + 1`, `clippedRows: 0`, nombres/labels con ellipsis.
- Rutas reales local y publicas con Playwright:
  - `partida-actual.html?server=comunidad-hispana-01`
  - `partida-actual.html?server=comunidad-hispana-02`
  - sin errores de consola ni `TypeError`.
- Endpoints publicos `current-match-*` con PowerShell: todos respondieron `200`.
- La auditoria Python no se repitio porque sigue bloqueada por TLS de `urllib` en este entorno:
  `CERTIFICATE_VERIFY_FAILED: Basic Constraints of CA cert not marked critical`.

Alcance:

- Se modifico solo CSS de frontend y esta task.
- TASK-261 queda en `ai/tasks/done` para cierre y commit aislado.
- No se tocaron assets fisicos, SVGs, PNGs, `frontend/assets/img/weapons/`, backend, scheduler, RCON, TeamKills, Elo/MMR, mapas, clans, brands, configuracion de servidores, `27001`, `ai/system-metrics.md` ni TASK-204.

## Change Budget

- Preferir menos de 5 archivos modificados.
- Preferir menos de 200 lineas cuando sea viable.
- Dividir en follow-up si el alcance crece.


