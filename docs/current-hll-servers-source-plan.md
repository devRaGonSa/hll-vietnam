# Current HLL Servers Source Plan

## Objective

Definir como mostrar en la web de HLL Vietnam un bloque provisional con
servidores actuales de Hell Let Loose sin presentarlos como si fueran datos de
HLL Vietnam ni depender todavia de una integracion real externa.

## Product Framing

- El bloque debe presentarse como referencia provisional para la comunidad.
- El copy debe mencionar de forma explicita "servidores actuales de Hell Let
  Loose" y evitar formulas ambiguas como "servidores HLL Vietnam".
- La UI debe dejar claro que el bloque sirve mientras no existan datos propios o
  mas cercanos al contexto final de HLL Vietnam.
- Si no hay datos disponibles, el estado vacio debe ser neutral y honesto, sin
  simular actividad inexistente.

## Recommended Fields For This Phase

Campos utiles para un bloque pequeno y entendible:

- `server_name`
- `status`
- `players`
- `max_players`
- `current_map`
- `region`

Campos opcionales solo si una fuente futura los ofrece de forma estable:

- `queue`
- `ping`
- `notes`
- `last_updated`

## Source Options

### Public external source

- Puede ser una API publica especializada, un listado publico o una consulta de
  servidor compatible con el juego actual.
- Ventaja: acerca la web a datos mas reales.
- Riesgo: cambios de formato, limites de uso, CORS, disponibilidad y dependencia
  de terceros.

### Controlled placeholder data

- Fuente recomendada para la primera implementacion.
- El backend expone un payload manual con forma realista y semantica estable.
- Permite validar UI, contrato y estados de error sin acoplar la web a una
  fuente externa todavia no validada.

### Stronger future integration

- Un adaptador backend dedicado podra sustituir el placeholder cuando exista una
  fuente fiable o un dataset controlado mantenido por la comunidad.
- La sustitucion debe preservar el contrato JSON para no romper al frontend.

## Risks And Restrictions

- Disponibilidad: una fuente externa puede caer o degradarse sin aviso.
- CORS: el frontend no debe depender de llamadas directas a terceros.
- Rate limits: una API publica puede limitar frecuencia o volumen.
- Formato: scraping o endpoints no oficiales pueden cambiar sin contrato.
- Mantenimiento: una integracion fragil crearia coste operativo prematuro.
- Identidad: el bloque no puede inducir a pensar que HLL Vietnam ya dispone de
  servidores propios o datos oficiales.

## Phased Strategy

### Phase 1: controlled mock

- `GET /api/servers` devuelve datos manuales con estructura estable.
- El payload debe incluir una marca de contexto provisional para indicar que los
  datos pertenecen al HLL actual.
- La landing puede consumir el endpoint con fallback local si el backend no esta
  disponible.

### Phase 2: backend adapter

- Sustituir el mock por un adaptador backend desacoplado de la fuente concreta.
- Mantener el mismo contrato principal de `items`.
- Introducir validacion basica de campos y fallback controlado si falla la
  fuente.

### Phase 3: replacement toward HLL Vietnam

- Reemplazar o mezclar progresivamente el bloque cuando existan datos mas
  representativos del contexto HLL Vietnam.
- Revisar naming, copy y campos para no arrastrar supuestos del juego actual.

## Explicitly Out Of Scope Now

- Integrar una fuente externa real.
- Hacer scraping.
- Consultar servidores reales desde el frontend.
- Anadir base de datos, cache o panel administrativo.
- Presentar el bloque como caracteristica definitiva del producto.

## Recommended Contract Shape

Ejemplo minimo de respuesta provisional:

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

## Handoff To Following Tasks

- Backend task: preparar el adaptador placeholder estable sobre este contrato.
- Frontend task: anadir un panel visual sobrio con etiqueta provisional y
  fallback seguro si el endpoint falla o no devuelve items.
