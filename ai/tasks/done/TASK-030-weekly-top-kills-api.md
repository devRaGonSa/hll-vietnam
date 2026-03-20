# TASK-030-weekly-top-kills-api

## Goal
Exponer una primera API histórica útil que devuelva el ranking de jugadores con más kills de la última semana para cada uno de los 2 servidores de la comunidad.

## Context
La primera necesidad histórica expresada para el proyecto es mostrar estadísticas como “jugadores con más kills de la última semana de cada servidor”. Una vez exista base mínima de ingesta y persistencia, la primera capa de valor debe ser un endpoint sencillo, estable y listo para alimentar futuras vistas o paneles.

## Steps
1. Revisar la estructura histórica persistida y la documentación del modelo de dominio.
2. Diseñar e implementar un endpoint o conjunto mínimo de endpoints para top kills semanales por servidor.
3. Definir un payload claro que incluya, como mínimo:
   - servidor
   - rango
   - jugador
   - kills semanales
   - rango temporal usado
4. Asegurar que la consulta se limita a la última semana real según la definición elegida por el proyecto.
5. Mantener una implementación clara y preparada para futuras métricas históricas.
6. Documentar el endpoint en backend.
7. No implementar todavía UI histórica en esta task.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/historical-stats-domain-model.md
- backend/README.md
- backend/app/routes.py
- backend/app/payloads.py
- cualquier módulo de persistencia histórica creado en tasks previas

## Expected Files to Modify
- backend/app/routes.py
- backend/app/payloads.py
- backend/README.md
- opcionalmente nuevos módulos de consulta histórica en backend

## Constraints
- No romper endpoints actuales.
- No añadir UI histórica todavía.
- No introducir librerías nuevas salvo necesidad muy justificada.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en una primera API histórica útil y estable.

## Validation
- Existe un endpoint histórico usable para top kills semanales por servidor.
- El endpoint funciona para los 2 servidores reales de la comunidad.
- El payload es claro y reutilizable.
- La documentación backend queda alineada.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.

## Outcome
- `backend/app/historical_storage.py` añade la consulta agregada semanal de kills por servidor.
- `backend/app/payloads.py` expone un payload estable para `top kills` semanales.
- `backend/app/routes.py` añade `GET /api/historical/top-kills/weekly?limit=10` con soporte opcional para `server_id`.
- `backend/README.md` documenta el endpoint y su payload.

## Validation Result
- Ejecutado desde `backend/`: `python -` resolviendo `/api/historical/top-kills/weekly?limit=5` vía `resolve_get_payload(...)`.
- Resultado: `HTTP 200` y rankings útiles para ambos servidores reales.
- Ejemplo validado:
  - `comunidad-hispana-01` devuelve ranking encabezado por `[LCM] Vask0`
  - `comunidad-hispana-02` devuelve ranking encabezado por `Juanko`

## Decision Notes
- Se expone primero un endpoint agregado por servidor para cubrir el caso de uso real expresado por el proyecto sin multiplicar rutas históricas prematuras.
- La ventana temporal queda definida como rodante de 7 días usando UTC.
