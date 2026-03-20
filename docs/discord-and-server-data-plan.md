# Discord And Server Data Plan

## Objective

Definir una base tecnica para exponer en la web datos de Discord y de futuros servidores de juego sin implementar todavia integraciones reales ni depender de servicios externos en esta fase.

## Discord Data Candidates

Bloques con sentido para la web:

- `invite_url`: enlace principal para entrar en la comunidad.
- `community_name`: nombre visible de la comunidad o del servidor.
- `cta_label`: texto de llamada a la accion para el boton de acceso.
- `approx_presence`: presencia aproximada o estado publico solo si existe una fuente publica fiable.
- `public_summary`: breve descripcion publica, reglas resumidas o mensaje de bienvenida.

## Game Server Data Candidates

Bloques con sentido para la web:

- `server_name`: nombre visible del servidor.
- `status`: online u offline.
- `current_map`: mapa actual si la fuente lo permite.
- `rotation`: rotacion o proximo mapa si la fuente es estable.
- `players`: jugadores conectados.
- `max_players`: capacidad maxima.
- `ping`: latencia aproximada si la consulta la devuelve.
- `region` o `notes`: metadatos operativos simples para la comunidad.

## Possible Discord Sources

### Public widget

- Util para obtener datos publicos basicos si el servidor lo tiene habilitado.
- Bueno para presencia aproximada o nombre visible.
- Limitado por la configuracion del propio servidor y por el alcance real del widget.

### External API or third-party integration

- Puede simplificar algunas lecturas, pero introduce dependencia de terceros, cambios de servicio y posibles limites de uso.
- Debe considerarse solo si aporta estabilidad y evita exponer credenciales en frontend.

### Own bot

- Da mas control a largo plazo.
- Exige credenciales, despliegue, permisos y operacion continua.
- No encaja en la fase actual del repositorio.

### Manual configured data

- Fuente mas segura para la primera fase.
- Sirve para `invite_url`, nombre de comunidad y textos publicos.
- Permite validar el contrato API y el consumo frontend sin depender de Discord real.

## Possible Game Server Sources

### Direct server queries

- Pueden dar estado, jugadores, mapa o ping segun el protocolo disponible.
- Exigen validar compatibilidad real con el juego, frecuencia de consulta y tolerancia a timeouts.

### External API

- Puede simplificar el acceso si existe una fuente especializada.
- Introduce dependencia externa, disponibilidad ajena y posible coste o rate limit.

### Mock or placeholder data

- Opcion recomendada para la primera fase.
- Permite fijar formato JSON, estados y experiencia de frontend sin acoplarse a infraestructura real.

### Manual updates

- Util para mostrar estado controlado o informacion operativa minima mientras no exista integracion tecnica fiable.
- Reduce riesgo en una etapa donde el backend aun es preparatorio.

## Risks And Restrictions

- Credenciales: bots o APIs privadas requieren secretos y una estrategia de almacenamiento segura.
- Rate limits: Discord o terceros pueden limitar frecuencia de consulta.
- Availability: widgets, APIs o consultas de servidor pueden fallar o cambiar sin previo aviso.
- Security: nunca debe exponerse en frontend una credencial ni una ruta administrativa.
- CORS: el frontend no deberia depender de llamadas directas a servicios externos si eso obliga a resolver CORS en cliente.
- Latency: consultas en tiempo real pueden degradar la web si no se amortiguan en backend.
- External dependency: cada integracion nueva aumenta coste operativo y puntos de fallo.

## Phased Strategy

### Phase 1: controlled placeholders

- Backend Python devuelve datos manuales o mock para `/api/discord` y `/api/servers`.
- La web usa esos datos solo cuando futuras tasks lo indiquen.
- No hay consultas reales a Discord ni a servidores.

### Phase 2: limited technical integration

- Evaluar una unica fuente publica o consulta sencilla por dominio.
- Mantener fallback manual si la fuente falla.
- Introducir observabilidad minima antes de ampliar alcance.

### Phase 3: real integration if justified

- Considerar bot propio, polling controlado o una integracion mas rica solo si aporta valor real a la comunidad.
- Revisar seguridad, operacion, cache y mantenimiento antes de consolidarlo.

## What Is Explicitly Out Of Scope Now

- Integrar Discord real.
- Consultar servidores reales de juego.
- Anadir base de datos.
- Implementar autenticacion o panel administrativo.
- Hacer llamadas directas desde el frontend a servicios externos.

## Recommended Implementation Order

1. Consolidar placeholders backend para `community`, `discord`, `trailer` y `servers`.
2. Definir consumo frontend con fallbacks visuales y orden de prioridad.
3. Validar una fuente publica o consulta tecnica pequena para Discord o servidores.
4. Decidir si merece la pena ampliar integraciones reales.
