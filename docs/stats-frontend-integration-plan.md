# Plan de integracion de Stats en frontend

## 1. Pagina prevista

- Pantalla objetivo: `frontend/stats.html` (nueva).
- Objetivo V1: pagina ligera, statically-safe, con componentes para:
  - buscador
  - resultados
  - panel de stats personales
  - resumen semanal
  - resumen mensual
  - bloque futuro de ranking anual top 20 (placeholder)

## 2. Navegacion

El cambio no debe romper Inicio, Historico ni Partida actual.

- Mantener `frontend/index.html` con su estructura actual.
- Cambios de navegacion propuestos:
  - Añadir un link `Stats` en el bloque de acciones del hero:
    - `href="./stats.html"`
    - texto: `Stats`
    - estilo reutilizando `.secondary-button` o variante especifica en CSS si se requiere.
  - En `frontend/historico.html`:
    - añadir boton de regreso a Inicio si no existe.
    - opcionalmente incluir acceso rapido a `stats.html` en el header.
  - En `partida-actual.html` (futuro, si usa una plantilla):
    - no modificar por ahora.
- Regla de compatibilidad:
  - No alterar rutas de `historico.html` ni de `partida-actual.html`.
  - Mantener rutas existentes (`./historico.html`, `./index.html`) intactas.

## 3. Componentes V1

- Buscador de jugador
  - Input para texto libre.
  - Boton de ejecucion.
  - Debounce/submit manual para evitar ruido.
  - Query query param `q`.
- Lista de resultados
  - Mostrar por fila:
    - `player_name`
    - `player_id` (texto de soporte)
    - `matches_considered`
    - `last_seen_at`
    - `servers_seen` (solo si se integra en payload final).
  - Cada fila habilita seleccion de jugador.
- Panel de estadisticas personales
  - Estado base despues de seleccionar jugador:
    - nombre y player_id
    - server/scope visible.
  - Datos por `GET /api/stats/players/{player_id}?timeframe=...&server_id=...`.
- Resumen semanal
  - Render a partir de `data.weekly_ranking` y `data` para la misma ventana.
- Resumen mensual
  - Render a partir de `data.monthly_ranking` y datos de ventana.
- Bloque anual futuro
  - Reservado en layout con estado:
    - `Proximo: ranking anual top 20`.
  - Sin llamada ni dependencia now.

## 4. Endpoints usados

- `GET /api/stats/players/search?q=<query>`
  - `q` obligatorio.
  - parametros recomendados V1:
    - `server_id` opcional (`all-servers` como default).
    - `limit` opcional.
- `GET /api/stats/players/{player_id}`
  - para semana: `timeframe=weekly`.
  - para mes: `timeframe=monthly`.
  - para cambios de scope: `server_id=all-servers|comunidad-hispana-01|comunidad-hispana-02`.

## 5. Estados de UI

- Loading
  - Skeleton o placeholder en buscador y lista de resultados.
  - Mensaje breve en paneles de resumen con estado neutro.
- Error
  - Mensaje tactico y silencioso en consola.
  - Mantener contenido previo visible.
- Sin resultados
  - estado vacio: `No se encontraron jugadores para esta busqueda`.
- Jugador sin stats
  - si `matches_considered == 0`:
    - mostrar `Sin actividad registrada en el periodo`.
- Backend no disponible
  - banner no intrusivo de estado.
  - no bloquear el resto de la pagina.

## 6. Identidad visual

- Mantener estilo militar / Vietnam / tactico / sobrio:
  - variables CSS existentes en `frontend/assets/css/styles.css`.
  - paleta actual.
  - tarjetas y borders similares a `panel`, `clan-card`, `server-card`.
- No introducir frameworks.
- Preferir reutilizacion:
  - `hero`, `panel`, `status-chip`, `secondary-button` y utilidades de layout existentes.
- Agregar estilos nuevos solo en `styles.css` si la combinacion base no cubre el layout.

## 7. Archivos esperados para implementacion futura

- `frontend/stats.html`
- `frontend/assets/js/stats.js`
- `frontend/assets/css/styles.css` (solo si necesario para grid, estados, card o tabla simple)
- `frontend/index.html` y/o `frontend/historico.html` para navegacion a Stats, sin tocar la logica de secciones actuales.

## Alcance de validacion

Esta task es un plan y no requiere pruebas automaticas.

- Verificar por dif:
  - solo `ai/tasks/pending/TASK-164-design-stats-frontend-integration-plan.md`
  - `docs/stats-frontend-integration-plan.md`
- Revisar que el plan respete las restricciones:
  - sin cambios backend
  - sin implementacion
  - sin ranking anual
  - sin elo/mmr
  - sin comunidad hispana #03
- Preparar siguiente task: implementacion de `frontend/stats.html` y `frontend/assets/js/stats.js` usando endpoints V1.

