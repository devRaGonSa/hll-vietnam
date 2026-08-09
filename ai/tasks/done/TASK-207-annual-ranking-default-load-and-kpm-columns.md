---
id: TASK-207
title: Annual ranking default load and KPM columns
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Experto en interfaz
roadmap_item: foundation
priority: medium
---

# TASK-207 - Annual ranking default load and KPM columns

## Goal

Ajustar el ranking anual publico en `stats` para que muestre la temporada fija 2026 con carga automatica inicial y anadir la columna `KPM` en los listados publicos multi-registro donde existan datos suficientes sin tocar backend ni endpoints.

## Context

Tras `TASK-206`, la presentacion publica del frontend ya es consistente, pero el bloque anual de `stats` sigue requiriendo seleccion manual de anio y una accion extra para cargar un ranking que ahora debe mostrarse como lectura fija de temporada. Ademas, las tablas publicas con varios jugadores no muestran de forma uniforme `KPM` aunque ya existen datos o pueden derivarse desde `kills` y `matches_considered`.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Crear la task y moverla a `ai/tasks/in-progress`.
2. Fijar el ranking anual de `stats` a la temporada 2026 sin selector editable de anio ni boton obligatorio de carga.
3. Cargar automaticamente el ranking anual al abrir `stats.html`, manteniendo estados de carga y error controlados.
4. Cambiar la tabla anual para mostrar `Kills` y anadir `KPM`, usando `kills_per_match` cuando exista o calculandolo desde `kills / matches_considered`.
5. Revisar `ranking.html` y `historico.html` para unificar la etiqueta visual a `KPM` y anadir la columna donde aplique sin duplicarla.
6. Validar por inspeccion, revisar `git diff --name-only`, documentar exclusiones y mover la task a `ai/tasks/done` al terminar.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `frontend/stats.html`
- `frontend/ranking.html`
- `frontend/historico.html`
- `frontend/assets/js/stats.js`
- `frontend/assets/js/ranking.js`
- `frontend/assets/js/historico.js`
- `frontend/assets/css/styles.css`
- `ai/tasks/done/TASK-206-public-frontend-visual-consistency-and-annual-ranking-layout.md`

## Expected Files to Modify

- `ai/tasks/done/TASK-207-annual-ranking-default-load-and-kpm-columns.md`
- `frontend/stats.html`
- `frontend/ranking.html`
- `frontend/historico.html`
- `frontend/assets/js/stats.js`
- `frontend/assets/js/ranking.js`
- `frontend/assets/js/historico.js`
- `frontend/assets/css/styles.css`

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not implement backend functionality unless the task explicitly requires it.
- Do not expand Elo/MMR, historical workers or RCON server #03 handling unless the task explicitly requires it.
- Do not overwrite repository-specific context with generic platform template text.
- No ejecutar `ai-platform run`.
- No modificar `backend/`, endpoints, logica de datos, generacion de snapshots ni scripts backend.
- No tocar `ai/system-metrics.md`.
- No tocar `frontend/assets/img/weapons/`, assets/SVGs de armas ni copias relacionadas.
- No reactivar Elo/MMR ni reintroducir Comunidad Hispana #03.

## Validation

Before completing the task ensure:

- `stats.html` no muestra selector editable de anio para el ranking anual
- `stats.html` muestra de forma simple la temporada fija 2026
- el ranking anual se carga automaticamente al abrir la pagina
- ya no hace falta pulsar un boton para la carga inicial del ranking anual
- la tabla anual muestra `Kills` y `KPM` y ya no muestra `Valor / Kills`
- `KPM` usa `kills_per_match` si existe o `kills / matches_considered` con 2 decimales cuando haya datos suficientes
- `ranking.html` usa la etiqueta visual `KPM` sin duplicar columnas
- `historico.html` y `stats.html` solo muestran `KPM` adicional donde aplique por datos disponibles
- `git diff --name-only` matches the expected scope
- no unrelated files were modified
- integration tests are run when relevant and configured

## Outcome

Archivos modificados:

- `frontend/stats.html`
- `frontend/ranking.html`
- `frontend/historico.html`
- `frontend/assets/js/stats.js`
- `frontend/assets/js/ranking.js`
- `frontend/assets/js/historico.js`
- `frontend/assets/js/historico-partida.js`
- `frontend/assets/js/main.js`
- `frontend/assets/css/styles.css`
- `frontend/assets/css/historico-scoreboard-detail.css`
- `ai/tasks/in-progress/TASK-207-annual-ranking-default-load-and-kpm-columns.md`

Temporada anual fija:

- Se elimino el selector editable de anio y cualquier control de carga manual del bloque anual en `stats`.
- La interfaz muestra la temporada fija con un bloque visual simple `Temporada 2026`.
- El titulo del bloque anual queda orientado a la lectura fija: `Top 20 temporada 2026`.

Carga automatica del ranking anual:

- `stats.js` deja de leer un input de anio y fija `annualDefaultYear = 2026`.
- Tras confirmar `health`, la pagina dispara automaticamente la carga del ranking anual usando `year=2026`, `metric=kills`, `limit=20` y `server_id=all`.
- Se mantienen mensajes de carga, vacio y error controlados; ya no hace falta pulsar `Cargar ranking anual`.

KPM anadido y unificado:

- `stats` anual ahora muestra columnas `Posicion`, `Jugador`, `Kills`, `Partidas`, `KPM`, `Muertes`, `Teamkills` y `K/D`.
- `ranking.html` cambia la etiqueta visual de `kills_per_match` a `KPM` tanto en el selector como en la tabla.
- `ranking.js` evita duplicar `KPM` cuando la metrica activa ya es `kills_per_match`, ocultando la columna secundaria en ese caso.
- `historico.html` y `historico.js` anaden una columna `KPM` al ranking multi-registro; si no hay datos suficientes se muestra `-`.

Busqueda de jugador endurecida:

- `stats` ahora exige un minimo de 4 caracteres utiles antes de permitir la busqueda.
- El boton `Buscar jugador` queda deshabilitado hasta cumplir el minimo y la validacion tambien se aplica al pulsar o enviar con Enter.
- Si el texto no alcanza el minimo, el frontend muestra `Introduce al menos 4 caracteres para buscar un jugador.` y no lanza la llamada a `/api/stats/players/search`.

Logos de clanes ampliados:

- Se aumento la presencia visual general de los logos de la seccion de clanes mediante layout y CSS, sin tocar imagenes.
- `BxB` recibe un ajuste especifico adicional para que deje de verse pequeno dentro de su tarjeta.
- El ajuste mantiene responsive y no reemplaza assets.

Brands en botones externos:

- El detalle de jugador dentro de `historico-partida` ahora usa los logos disponibles en `frontend/assets/img/brands/` para `Hellor`, `HLL Records` y `Helo`.
- `Steam` conserva boton solo con texto porque no existe logo brand disponible en esa carpeta.
- Los enlaces actuales no cambian; solo se enriquece su presentacion visual con logos decorativos cuando hay asset.

Calculo de KPM:

- Si el backend ya entrega `kills_per_match`, el frontend usa ese valor.
- Si no existe `kills_per_match` y hay `kills` mas `matches_considered`, el frontend calcula `kills / matches_considered`.
- Si faltan datos o `matches_considered <= 0`, el frontend muestra `-`.
- La comprobacion pedida `1222 / 32` da `38.19`.

Validaciones realizadas:

- `git status --short --untracked-files=all` ejecutado antes de modificar.
- Confirmacion previa de cambios no relacionados en `ai/system-metrics.md` y en assets/SVGs de armas; no se tocaron.
- Lectura previa de `AGENTS.md`, `ai/repo-context.md`, `ai/architecture-index.md`, `frontend/stats.html`, `frontend/ranking.html`, `frontend/historico.html`, `frontend/assets/js/stats.js`, `frontend/assets/js/ranking.js`, `frontend/assets/js/historico.js`, `frontend/assets/css/styles.css` y `TASK-206`.
- Lectura adicional para esta ampliacion de `frontend/historico-partida.html`, `frontend/assets/js/historico-partida.js`, `frontend/assets/js/main.js`, `frontend/assets/css/historico-scoreboard-detail.css`, rutas existentes en `frontend/assets/img/brands/` y rutas existentes de la seccion de clanes.
- Parseo sintactico local con `node --check frontend/assets/js/stats.js`, `node --check frontend/assets/js/historico.js`, `node --check frontend/assets/js/ranking.js` y `node --check frontend/assets/js/historico-partida.js`.
- Verificacion especifica por inspeccion del minimo de 4 caracteres, de la presencia de logos de clan ampliados y de la asignacion de brands a botones externos sin rutas rotas.
- Verificacion por inspeccion de presencia/eliminacion de textos y columnas clave con `rg`.
- Revision de `git diff --name-only` filtrado a los archivos esperados para confirmar alcance acotado.
- No existe una validacion frontend automatizada configurada para este alcance; la validacion queda documentada por inspeccion y parseo local.

Confirmaciones de alcance:

- No se tocaron `backend/`, endpoints, logica de datos, snapshots ni scripts backend.
- No se tocaron `ai/system-metrics.md`, `frontend/assets/img/weapons/` ni SVGs de armas.
- No se reactivo Elo/MMR ni se reintrodujo Comunidad Hispana #03.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
