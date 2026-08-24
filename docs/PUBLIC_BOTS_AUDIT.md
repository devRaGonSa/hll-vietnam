# Auditoría pública de bots y comandos

Auditoría read-only realizada el 24 de agosto de 2026 sobre la VPS desplegada. La comprobación cruzó estado de unidades y temporizadores, configuración efectiva de los tres targets CRCON, código cargado en los procesos, configuración YAML efectiva y actividad reciente. No se ejecutaron comandos de juego o Discord, no se enviaron mensajes y no se incluyeron credenciales, endpoints, identificadores privados, expresiones de moderación ni datos de jugadores.

`ACTIVE` significa que el mecanismo está habilitado, no está en simulación y su proceso o target está activo. `DRY_RUN` identifica procesos que observan o registran pero no aplican la acción. Una plantilla deshabilitada puede tener instancias activas; la matriz refleja la instancia efectiva. En particular, la descripción histórica de la unidad de Custom Seed aún dice “dry-run”, pero el proceso efectivo carga `bot.dry_run: false` y tiene habilitadas sus acciones; por eso se clasifica como `ACTIVE`.

## Matriz sanitizada

| Mecanismo | Estado | Ámbito | Tipo | Público | Motivo |
|-----------|--------|--------|------|---------|--------|
| Respuestas de chat configuradas (`!help`, `!discord`, `!wkm`, `!push`, `!vip`) | ACTIVE | HLL #1, HLL #2, HLL Vietnam | CHAT_COMMAND | Sí | Configuración efectiva habilitada e idéntica en los tres targets. |
| Cambio de bando habilitado (`!switch`, `@switch`) | ACTIVE | HLL #1, HLL #2, HLL Vietnam | CHAT_COMMAND | Sí | Acción habilitada para jugadores con permiso y bajo la condición pública de población. |
| Redespliegue (`!redeploy`, `!r`) | ACTIVE | HLL #1, HLL #2, HLL Vietnam | CHAT_COMMAND | Sí | Acción habilitada para cualquier jugador, sin argumentos. |
| Solicitud de nodos (`!nodos`) | ACTIVE | HLL #1, HLL #2 | CHAT_COMMAND | Sí | Configuración habilitada y método cargado en los dos targets clásicos; ausente en Vietnam. |
| Votación de mapa (`!votemap`, `!vm`) | ACTIVE | HLL #1, HLL #2, HLL Vietnam | CHAT_COMMAND | Sí | Función habilitada sin restricción VIP o de flags. |
| Estadísticas históricas (`!me`) | ACTIVE | HLL #1, HLL #2, HLL Vietnam | CHAT_COMMAND | Sí | Herramienta cargada en los tres supervisores y habilitada para los tres targets. |
| Clasificación en vivo (`!top`) | ACTIVE | HLL #1, HLL #2, HLL Vietnam | CHAT_COMMAND | Sí | Herramienta cargada y habilitada en los tres targets. |
| `!admin` de juego | INACTIVE | HLL #1, HLL #2, HLL Vietnam | CHAT_COMMAND | No | Existe en la configuración, pero cada entrada está deshabilitada. |
| Alias histórico `!historico` | LEGACY | Código de porting no desplegado | CHAT_COMMAND | No | Se encontró en una copia de porting, no en la configuración cargada. |
| Estadísticas privadas al conectar | ACTIVE | HLL #1, HLL #2, HLL Vietnam | GAME_AUTOMATION | Sí | El resumen histórico está habilitado al conectar y también bajo demanda con `!me`. |
| Topstats y recompensas al final de partida | ACTIVE | HLL #1, HLL #2, HLL Vietnam | GAME_AUTOMATION | Sí | El complemento cargado muestra rankings y procesa ganadores elegibles. |
| Vote Map | ACTIVE | HLL #1, HLL #2, HLL Vietnam | CRCON_FEATURE | Sí | Votación, ayuda, recordatorios y opt-out habilitados. |
| Seed VIP | ACTIVE | HLL #1, HLL #2, HLL Vietnam | CRCON_FEATURE | Sí | Habilitado y no dry-run en los tres targets; concede VIP elegible de forma real. |
| Programación de Seed VIP | ACTIVE | Tres targets CRCON | OPERATIONS_ONLY | No | Temporizador activo que gestiona el horario del proceso; el detalle operativo no aporta una acción al jugador. |
| VIP Rewards semanal | ACTIVE | HLL #1, HLL #2 | GAME_AUTOMATION | Sí | Motor activo, no dry-run y con entrega live; la página enlaza a las reglas VIP en vez de duplicarlas. |
| Commander AFK | DRY_RUN | HLL #1, HLL #2 | GAME_AUTOMATION | No | Las instancias observan, pero la configuración efectiva está en dry-run y deshabilita avisos y expulsiones. |
| Custom Seed | ACTIVE | HLL #1, HLL #2 | GAME_AUTOMATION | Sí | Instancias activas, no dry-run, con avisos y acciones de cumplimiento habilitadas. |
| Automod de seeding CRCON | ACTIVE | HLL #1, HLL #2, HLL Vietnam | CRCON_FEATURE | Sí | Habilitado, no dry-run y con anuncios/acciones habilitados. |
| Automod de nivel | ACTIVE | HLL #1, HLL #2 | CRCON_FEATURE | Sí | Habilitado y no dry-run en los targets clásicos. |
| Automod de nivel en Vietnam | INACTIVE | HLL Vietnam | CRCON_FEATURE | No | Deshabilitado en la configuración efectiva de Vietnam. |
| Automod de escuadras sin oficial | ACTIVE | HLL #1, HLL #2, HLL Vietnam | CRCON_FEATURE | Sí | Habilitado y no dry-run en los tres targets. |
| Automod de tanque en solitario | INACTIVE | HLL #1, HLL #2, HLL Vietnam | CRCON_FEATURE | No | Deshabilitado en los tres targets. |
| Control de nombres | DRY_RUN | HLL #1, HLL #2 | GAME_AUTOMATION | No | El proceso está activo, pero su entorno efectivo solo registra detecciones y no avisa ni sanciona. |
| Control de palabras en Discord | ACTIVE | Canales de Discord configurados | DISCORD_BOT | Sí | Detecta posibles incumplimientos y alerta a moderación; no elimina ni sanciona por sí mismo. |
| Kill ticker / top de bajas | ACTIVE | HLL #1, HLL #2 | GAME_AUTOMATION | Sí | Instancias activas y no dry-run; alternan top de bajas y avisos de votación en el broadcast. |
| AutoBroadcast nativo CRCON | INACTIVE | HLL #1, HLL #2, HLL Vietnam | CRCON_FEATURE | No | Deshabilitado en los tres targets; el broadcast visible de #1/#2 lo gestiona Kill Ticker. |
| Watch Kill Rate | INACTIVE | HLL #1, HLL #2, HLL Vietnam | CRCON_FEATURE | No | Deshabilitado en los tres targets. |
| Bot informativo de Discord | ACTIVE | Discord; HLL #1 y HLL #2 | DISCORD_BOT | Sí | Responde consultas de jugadores y duración de partida en los canales permitidos. |
| Bot de tickets | ACTIVE | Discord | DISCORD_BOT | Sí | Publica instrucciones de soporte al crearse tickets de categorías conocidas. |
| Bot de reinicio y utilidades internas | ACTIVE | Discord/operaciones | OPERATIONS_ONLY | No | Sus comandos gestionan operaciones o tareas restringidas, no una función pública general. |
| Monitores de jugadores y gráfica | ACTIVE | HLL #1, HLL #2 | OPERATIONS_ONLY | No | Temporizadores operativos sin interacción pública. |

## Comandos de chat de juego verificados

Los comandos de respuesta configurables (`!help`, `@help`, `!discord`, `!wkm`, `!push`, `!vip`, `!switch`, `@switch`, `!redeploy`, `!r` y `!nodos`) distinguen mayúsculas y minúsculas y se activan por palabra exacta. No tienen argumentos configurados ni cooldown/limitación por partida. Las condiciones indicadas abajo se evalúan antes de aplicar la acción.

`!me`, `!top`, `!votemap` y `!vm` no distinguen mayúsculas y minúsculas. `!me` y `!top` requieren que el mensaje completo sea el comando. La familia Vote Map acepta los argumentos detallados en la tabla.

| Comando exacto | Estado | Público | Quién puede usarlo | Efecto/respuesta | Argumentos y límites | Servidores |
|----------------|--------|---------|--------------------|------------------|----------------------|------------|
| `!help`, `@help` | ACTIVE | Sí | Cualquier jugador | Mensaje privado con el resumen configurado. | Sin argumentos; sin cooldown configurado. | Los tres |
| `!discord` | ACTIVE | Sí | Cualquier jugador | Mensaje privado con la invitación oficial. | Sin argumentos; sin cooldown configurado. | Los tres |
| `!me` | ACTIVE | Sí | Cualquier jugador | Mensaje privado con estadísticas históricas acumuladas. | Sin argumentos; no distingue mayúsculas; sin cooldown configurado. | Los tres |
| `!wkm` | ACTIVE | Sí | Cualquier jugador | Mensaje privado con el último némesis y arma registrados. | Sin argumentos; sin cooldown configurado. | Los tres |
| `!top` | ACTIVE | Sí | Cualquier jugador | Mensaje privado con rankings de la partida actual. | Sin argumentos; no distingue mayúsculas; sin cooldown configurado. | Los tres |
| `!vip` | ACTIVE | Sí | Cualquier jugador | Mensaje privado con la caducidad VIP conocida. | Sin argumentos; sin cooldown configurado. | Los tres |
| `!push` | ACTIVE | Sí | Cualquier jugador | Mensaje privado informativo sobre el equipo competitivo. | Sin argumentos; sin cooldown configurado. | Los tres |
| `!switch`, `@switch` | ACTIVE | Sí | Jugadores que tienen el permiso configurado | Cambia inmediatamente al jugador de bando. | Sin argumentos; disponible con menos de 50 jugadores; sin cooldown configurado. | Los tres |
| `!redeploy`, `!r` | ACTIVE | Sí | Cualquier jugador | Aplica al propio jugador la acción de redespliegue rápido. | Sin argumentos; sin cooldown configurado. | Los tres |
| `!votemap`, `!vm` | ACTIVE | Sí | Cualquier jugador | Muestra la selección del siguiente mapa. | Sin argumentos; no distingue mayúsculas. | Los tres |
| `!votemap N`, `!vm N` | ACTIVE | Sí | Cualquier jugador | Registra o actualiza el voto para la opción `N`. | Un número de la selección vigente; sin cooldown configurado. | Los tres |
| `!votemap help`, `!vm help` | ACTIVE | Sí | Cualquier jugador | Muestra ayuda privada. | Sin argumentos adicionales; no distingue mayúsculas. | Los tres |
| `!votemap never`, `!vm never` | ACTIVE | Sí | Cualquier jugador | Desactiva para ese jugador los recordatorios de Vote Map. | Sin argumentos adicionales. | Los tres |
| `!votemap allow`, `!vm allow` | ACTIVE | Sí | Cualquier jugador | Reactiva los recordatorios de Vote Map. | Sin argumentos adicionales. | Los tres |
| `!vm add` | ACTIVE | Sí | Cualquier jugador | Muestra la ayuda para proponer mapa o registra una propuesta y su voto. | `<mapa> [modo] [atacante] [entorno]`; sin cooldown configurado. | Los tres |
| `!nodos` | ACTIVE | Sí | Comandante del equipo | Envía un mensaje privado a los ingenieros conectados de su bando. Si no hay ingenieros, no se envía ningún aviso. | Sin argumentos; sin cooldown ni límite por partida configurados. | HLL #1 y HLL #2 |

### Resultado específico de `!nodos`

La búsqueda encontró el método desplegado, la entrada efectiva del comando y las imágenes activas que lo contienen en HLL #1 y HLL #2. El método comprueba que quien lo solicita ocupa el rol de comandante, obtiene únicamente ingenieros de su equipo y les envía el aviso privado configurado. No está configurado en HLL Vietnam. No se encontró cooldown, límite por partida ni argumentos. Las apariciones aisladas en código sin una entrada efectiva no se trataron como disponibilidad.

## Comandos públicos de Discord

| Comando exacto | Estado | Público | Quién puede usarlo | Efecto | Ámbito |
|----------------|--------|---------|--------------------|--------|--------|
| `-server1 players`, `-server2 players` | ACTIVE | Sí | Miembros en los canales habilitados | Muestra jugadores conectados y paginación por reacciones. | HLL #1 y HLL #2 |
| `-server1 tiempo`, `-server2 tiempo` | ACTIVE | Sí | Miembros en los canales habilitados | Muestra la duración de la partida actual. | HLL #1 y HLL #2 |

El código contiene una función `-server3`, pero el target 3 no está en la lista efectiva de servidores activos del bot; responde como inactivo y no se publica. Los comandos de mantenimiento de listas, reinicio y gestión de palabras requieren contexto o roles internos y quedan fuera de la guía pública.

## Evidencia operativa sanitizada

- Unidades activas inspeccionadas: bot informativo, Commander AFK #1/#2, control de palabras, Custom Seed #1/#2, Kill Ticker #1/#2, control de nombres, bot interno de reinicio, tickets y VIP Rewards.
- Temporizadores inspeccionados: programación de Seed VIP y monitores de jugadores/gráfica.
- CRCON efectivo inspeccionado en HLL #1, HLL #2 y HLL Vietnam: chat commands, RCON chat commands, Vote Map, Seed VIP, AutoBroadcast, automods de nivel/seeding/sin oficial/tanque en solitario y Watch Kill Rate.
- Los tres targets CRCON estaban activos. Seed VIP, Vote Map, chat, topstats e histórico estaban habilitados en los tres. Las instancias del Kill Ticker y Custom Seed estaban procesando eventos recientes en #1/#2.
- La ventana reciente de diarios mostró actividad continua en Commander AFK, Custom Seed, Kill Ticker y VIP Rewards. Los conteos se revisaron sin copiar nombres, IDs ni líneas crudas al documento.
- Las plantillas de Kill Ticker aparecen deshabilitadas como plantilla, pero las instancias #1 y #2 están cargadas y activas. Se clasifican por estado efectivo.

## Criterio editorial

La página pública explica efectos útiles y ámbitos, pero omite nombres de procesos, rutas, intervalos de sondeo, expresiones y listas de moderación, contadores internos, identificadores, endpoints y procedimientos de administración. Commander AFK y el control de nombres se conservan en esta auditoría para justificar su exclusión, sin presentarlos como funciones activas. Las reglas de recompensas y seeding se enlazan a `frontend/vip.html`; las reglas de conducta se enlazan a `frontend/normativa.html`.
