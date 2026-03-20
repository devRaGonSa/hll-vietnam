# Frontend Backend Contract

## Objetivo

Definir un contrato inicial y pequeno entre la landing actual y el futuro backend Python sin implementar todavia integraciones reales ni comprometer detalles de infraestructura antes de tiempo.

## Estado actual

- Frontend: landing estatica sin consumo de API
- Backend: bootstrap Python con `GET /health`
- Integraciones reales: no implementadas

## Convenciones generales

- Todas las respuestas usan JSON.
- Los nombres de campos usan `snake_case`.
- `status` es obligatorio en todas las respuestas.
- Las respuestas exitosas usan `status: "ok"`.
- Las respuestas de error usan `status: "error"` y un campo `message`.
- Cuando un endpoint sea solo placeholder o aun no tenga datos reales, puede responder datos controlados o quedar documentado como previsto hasta una task posterior.

## Estructura base de respuesta

Respuesta correcta:

```json
{
  "status": "ok",
  "data": {}
}
```

Respuesta de error minima:

```json
{
  "status": "error",
  "message": "Route not found"
}
```

## Endpoints

### `GET /health`

- Proposito: comprobar que el backend bootstrap esta levantado.
- Metodo HTTP: `GET`
- Ruta: `/health`
- Estado actual: implementado

Ejemplo JSON:

```json
{
  "status": "ok",
  "service": "hll-vietnam-backend",
  "phase": "bootstrap"
}
```

### `GET /api/community`

- Proposito: devolver contenido resumido de presentacion de la comunidad para bloques de texto o estadisticas futuras.
- Metodo HTTP: `GET`
- Ruta: `/api/community`
- Estado actual: previsto

Ejemplo JSON:

```json
{
  "status": "ok",
  "data": {
    "title": "Comunidad Hispana HLL Vietnam",
    "summary": "Punto de encuentro para jugadores, escuadras y comunidad.",
    "discord_invite_url": "https://discord.com/invite/PedEqZ2Xsa"
  }
}
```

### `GET /api/trailer`

- Proposito: exponer la informacion del trailer que hoy esta fija en la landing.
- Metodo HTTP: `GET`
- Ruta: `/api/trailer`
- Estado actual: previsto

Ejemplo JSON:

```json
{
  "status": "ok",
  "data": {
    "video_url": "https://www.youtube.com/embed/JzYzYNVWZ_A",
    "title": "Trailer HLL Vietnam",
    "provider": "youtube"
  }
}
```

### `GET /api/discord`

- Proposito: centralizar la informacion publica del acceso a Discord sin integrar todavia datos reales del servidor.
- Metodo HTTP: `GET`
- Ruta: `/api/discord`
- Estado actual: placeholder

Ejemplo JSON:

```json
{
  "status": "ok",
  "data": {
    "invite_url": "https://discord.com/invite/PedEqZ2Xsa",
    "label": "Unirse al Discord",
    "availability": "manual"
  }
}
```

### `GET /api/servers`

- Proposito: exponer un bloque provisional de servidores actuales de Hell Let Loose como referencia temporal para la comunidad.
- Metodo HTTP: `GET`
- Ruta: `/api/servers`
- Estado actual: placeholder implementado

Ejemplo JSON:

```json
{
  "status": "ok",
  "data": {
    "title": "Servidores actuales de Hell Let Loose",
    "context": "current-hll-reference",
    "source": "controlled-placeholder",
    "items": [
      {
        "server_name": "HLL ESP Tactical Rotation",
        "status": "online",
        "players": 74,
        "max_players": 100,
        "current_map": "Sainte-Marie-du-Mont",
        "region": "EU"
      }
    ]
  }
}
```

Notas del placeholder actual:

- El contenido representa servidores actuales de Hell Let Loose, no servidores de HLL Vietnam.
- `context` permite al frontend etiquetar el bloque como referencia provisional.
- `source` indica que la respuesta actual sale de datos controlados del backend.

### `GET /api/servers/latest`

- Proposito: devolver el ultimo snapshot conocido por servidor desde la persistencia local.
- Metodo HTTP: `GET`
- Ruta: `/api/servers/latest`
- Estado actual: implementado para validacion tecnica

Ejemplo JSON:

```json
{
  "status": "ok",
  "data": {
    "title": "Ultimo estado conocido de servidores",
    "context": "current-hll-history",
    "source": "local-snapshot-storage",
    "items": [
      {
        "server_id": 1,
        "external_server_id": "hll-esp-tactical-rotation",
        "server_name": "HLL ESP Tactical Rotation",
        "region": "EU",
        "captured_at": "2026-03-20T08:45:20.802006Z",
        "status": "online",
        "players": 74,
        "max_players": 100,
        "current_map": "Sainte-Marie-du-Mont"
      }
    ]
  }
}
```

### `GET /api/servers/history`

- Proposito: devolver una ventana simple de snapshots recientes desde la persistencia local.
- Metodo HTTP: `GET`
- Ruta: `/api/servers/history`
- Parametros opcionales: `limit` entre `1` y `100`
- Estado actual: implementado para validacion tecnica

Ejemplo JSON:

```json
{
  "status": "ok",
  "data": {
    "title": "Historial reciente de servidores",
    "context": "current-hll-history",
    "source": "local-snapshot-storage",
    "limit": 20,
    "items": []
  }
}
```

### `GET /api/servers/{id}/history`

- Proposito: devolver una historia basica de snapshots para un servidor concreto.
- Metodo HTTP: `GET`
- Ruta: `/api/servers/{id}/history`
- Parametros opcionales: `limit` entre `1` y `100`
- Identificadores aceptados: `server_id` numerico interno o `external_server_id`
- Estado actual: implementado para validacion tecnica

Ejemplo JSON:

```json
{
  "status": "ok",
  "data": {
    "title": "Historial por servidor",
    "context": "current-hll-history",
    "source": "local-snapshot-storage",
    "server_id": "hll-esp-tactical-rotation",
    "limit": 20,
    "items": []
  }
}
```

## Consumo previsto desde frontend

- El frontend deberia llamar primero a `GET /health` solo para comprobaciones tecnicas o entornos de desarrollo, no para condicionar el render basico de la landing.
- Los endpoints de contenido (`/api/community`, `/api/trailer`, `/api/discord`, `/api/servers`) deberian consumirse con `fetch`.
- Si una llamada falla, la landing debe conservar un fallback estatico mientras exista contenido fijo en `index.html`.
- La futura migracion debe reemplazar valores hardcoded de forma incremental, endpoint por endpoint.

## Notas de alcance

- Este contrato no introduce autenticacion.
- Este contrato no define base de datos.
- Este contrato no integra Discord ni servidores reales.
- La implementacion de estos endpoints queda para tasks posteriores.
