# Stats Database Schema Foundation

## Objective

Definir una base de almacenamiento simple y reutilizable para snapshots de
servidores y estadisticas iniciales, sin comprometer todavia una base de datos
productiva concreta.

## Design Principles

- naming generico reutilizable para HLL actual y futuro HLL Vietnam
- separacion entre identidad de servidor y observaciones historicas
- persistir primero solo lo necesario para reconstruir actividad basica
- dejar espacio para multiples fuentes sin acoplar el modelo a una integracion
  unica

## Proposed Core Entities

### `game_sources`

Proposito:
describir el contexto del juego o dominio de origen de los datos.

Campos principales:

- `id`
- `slug`
- `display_name`
- `provider_kind`
- `is_active`
- `created_at`
- `updated_at`

Notas:

- `slug` puede tomar valores como `current-hll` y en el futuro otros contextos
  mas cercanos a HLL Vietnam.
- Esta entidad evita incrustar el juego en cada nombre de tabla.

### `servers`

Proposito:
mantener la identidad estable de cada servidor observado.

Campos principales:

- `id`
- `game_source_id`
- `external_server_id` nullable
- `server_name`
- `region` nullable
- `first_seen_at`
- `last_seen_at`
- `created_at`
- `updated_at`

Claves y relaciones:

- primary key en `id`
- foreign key a `game_sources.id`
- unique recomendado sobre `game_source_id` + `external_server_id` cuando el
  origen entregue identificador externo fiable

Notas:

- `server_name` no debe usarse como clave unica porque puede cambiar.
- `last_seen_at` resume la ultima observacion conocida sin sustituir a los
  snapshots historicos.

### `server_snapshots`

Proposito:
registrar cada captura puntual normalizada de un servidor.

Campos principales:

- `id`
- `server_id`
- `captured_at`
- `status`
- `players`
- `max_players`
- `current_map` nullable
- `source_name`
- `raw_payload_ref` nullable
- `created_at`

Claves y relaciones:

- primary key en `id`
- foreign key a `servers.id`
- index recomendado sobre `server_id` + `captured_at`

Notas:

- `status`, `players`, `max_players` y `current_map` son la base a persistir
  desde la primera fase.
- `raw_payload_ref` queda como referencia opcional para trazabilidad futura si
  el backend decide guardar artefactos crudos fuera de esta tabla.

## Initial Statistics Layer

No es necesario persistir metricas complejas desde el inicio. La primera capa
de estadisticas puede documentarse como derivada de `server_snapshots`.

Vistas o agregaciones recomendadas para una siguiente fase:

- ultima observacion por servidor
- pico de jugadores por servidor en una ventana temporal
- numero de snapshots online por servidor
- ultima vez visto online

Si mas adelante aparecen necesidades de rendimiento o cuadros de mando
persistentes, podra anadirse una tabla de agregados sin cambiar la base del
modelo.

## What To Persist First

Persistir por snapshot:

- `server_id`
- `captured_at`
- `status`
- `players`
- `max_players`
- `current_map` cuando exista
- `source_name`

Puede derivarse despues:

- tendencias
- medias por periodo
- picos historicos
- porcentaje de disponibilidad
- rankings

## Technology Position

El repositorio todavia no fija una tecnologia de persistencia productiva. La
base del esquema debe entenderse como modelo logico compatible con el backend en
Python y trasladable despues a la opcion de almacenamiento que se valide en una
task especifica.

En esta fase no se anaden migraciones, ORM ni ficheros de base de datos.

## Open Questions For Future Tasks

- que fuente aportara un identificador externo suficientemente estable
- con que frecuencia debe capturarse un snapshot
- si conviene guardar payload crudo completo o solo referencias
- cuando merece la pena materializar agregados persistentes
