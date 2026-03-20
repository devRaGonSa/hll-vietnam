# Current HLL Data Ingestion Plan

## Objective

Definir una estrategia tecnica reutilizable para ingerir datos del Hell Let
Loose actual como banco de pruebas del futuro ecosistema HLL Vietnam, sin
implementar todavia una ingesta productiva completa.

## Initial Data Scope

Los primeros campos a capturar deben cubrir el bloque provisional de
servidores y preparar historicos minimos:

- `server_name`
- `status`
- `players`
- `max_players`
- `current_map` si la fuente lo permite
- `captured_at`
- `source`
- `external_server_id` o identificador equivalente si la fuente lo ofrece

Campos como `queue`, `ping`, `rotation` o `notes` quedan como opcionales para
fases posteriores y no deben bloquear el bootstrap.

## Snapshot Concept

Un snapshot representa el estado observado de un servidor en un momento
concreto. No es un perfil estatico del servidor, sino una captura puntual con
timestamp.

Cada snapshot debe permitir:

- reconstruir una serie temporal simple por servidor
- detectar cambios de estado online u offline
- medir evolucion basica de jugadores y capacidad
- conservar la procedencia de la captura

El identificador estable del servidor y el `captured_at` deben separar la
identidad del servidor de cada observacion historica.

## Ingestion Source Options

### Phase-safe controlled payload

- Fuente recomendada para el inicio.
- Permite probar el pipeline con datos mock o manuales servidos por backend.
- Fija el contrato de entrada y la normalizacion sin depender de terceros.

### Public external source

- Puede ser una API publica o un listado mantenido por terceros.
- Acerca el banco de pruebas a datos reales.
- Exige validar formato, disponibilidad, limites de uso y estabilidad antes de
  consolidarlo.

### Direct server query or intermediary adapter

- Puede ofrecer datos mas cercanos al estado real del servidor.
- Introduce mayor complejidad tecnica, posibles timeouts y dependencia del
  protocolo soportado.
- Debe encapsularse detras de un adaptador backend, no exponerse al frontend.

## Normalization Baseline

La captura y la fuente no deben definir el contrato interno final. La
arquitectura debe separar:

1. lectura de datos crudos
2. normalizacion a un modelo comun
3. produccion de snapshots consistentes

La normalizacion inicial debe garantizar:

- naming estable en `snake_case`
- `status` reducido a valores controlados como `online`, `offline` o `unknown`
- enteros para `players` y `max_players` cuando existan
- `captured_at` generado en backend
- conservacion del nombre de fuente para trazabilidad

## Risks And Limits

- Disponibilidad de terceros: una fuente publica puede dejar de responder sin
  aviso.
- Cambios de formato: scraping o APIs no oficiales pueden romper el adaptador.
- Rate limits: las consultas frecuentes pueden exigir cache o polling mas
  espaciado.
- Latencia: una consulta lenta no debe trasladarse directamente al frontend.
- CORS: el frontend no debe llamar a fuentes externas para este flujo.
- Fiabilidad: diferentes fuentes pueden discrepar en jugadores, mapa o estado.
- Dependencia no oficial: una integracion fragil no debe convertirse en pieza
  critica del producto.

## Phased Architecture

### Phase 1: controlled payload and stable structure

- Mantener un payload controlado como base de `/api/servers`.
- Definir el modelo normalizado esperado para servidores y snapshots.
- No almacenar historico real todavia.

### Phase 2: snapshot collector with real or near-real source

- Introducir un colector backend desacoplado de la fuente concreta.
- Permitir ejecucion manual o periodica en entorno de desarrollo.
- Generar snapshots consistentes listos para futura persistencia.

### Phase 3: historical use and basic statistics

- Persistir snapshots.
- Calcular metricas iniciales como actividad por servidor, picos de jugadores o
  ultima vez visto online.
- Mantener el modelo generico para reutilizarlo con HLL Vietnam cuando existan
  datos mas representativos.

## Explicitly Out Of Scope Now

- ingesta real completa en produccion
- scraping productivo
- base de datos funcional
- tareas periodicas operativas
- metricas avanzadas o paneles analiticos
- cambios visibles en frontend

## Handoff To Following Tasks

- `TASK-019` debe convertir este plan en una base de esquema para persistir
  servidores y snapshots.
- `TASK-020` debe preparar un bootstrap pequeno del colector en Python con
  separacion entre fuente, normalizacion y snapshot.
