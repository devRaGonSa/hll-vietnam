# TASK-048-add-server-03-historical-source-and-ingestion

## Goal
Añadir el tercer servidor histórico de la comunidad (`https://scoreboard.comunidadhll.es:3443/`) a la capa histórica del proyecto, dejándolo preparado para ingesta, snapshots y consumo posterior por la UI propia.

## Context
Ahora mismo el proyecto trabaja con dos servidores históricos de comunidad, pero existe un tercer servidor real:
- `https://scoreboard.comunidadhll.es:3443/`

El sistema debe poder tratarlo como una tercera fuente histórica formal, no como un caso manual o externo, manteniendo la misma arquitectura de ingestión, persistencia y snapshots propia del proyecto.

## Steps
1. Revisar cómo están definidos hoy los servidores históricos actuales.
2. Añadir la configuración y el mapeo del tercer servidor con una identidad estable, por ejemplo:
   - `comunidad-hispana-03`
3. Asegurar que la capa de ingestión histórica puede consultar la fuente CRCON JSON del puerto `3443`.
4. Preparar la persistencia histórica para ese servidor:
   - matches
   - players
   - stats por match
   - checkpoints/backfill
5. Integrar el tercer servidor en la capa de snapshots:
   - resumen
   - rankings semanales
   - partidas recientes
6. Ajustar documentación y configuración operativa para reflejar que ya existen tres servidores históricos.
7. No exponer todavía UI nueva si no es imprescindible en esta task.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/config.py
- backend/app/historical_ingestion.py
- backend/app/historical_storage.py
- backend/app/historical_snapshot_storage.py
- backend/app/historical_snapshots.py
- backend/app/payloads.py
- backend/app/routes.py
- docs/historical-crcon-source-discovery.md
- docs/historical-domain-model.md

## Expected Files to Modify
- backend/app/config.py
- backend/app/historical_ingestion.py
- backend/app/historical_storage.py
- backend/app/historical_snapshot_storage.py
- backend/app/historical_snapshots.py
- backend/app/payloads.py
- backend/app/routes.py
- backend/README.md
- opcionalmente documentación técnica adicional

## Constraints
- No usar A2S para el histórico del servidor #03.
- No crear páginas externas o dependientes de la comunidad.
- No romper los servidores #01 y #02.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en registrar correctamente el servidor #03 en la plataforma histórica.

## Validation
- El servidor #03 queda definido con identidad estable en backend.
- La ingesta histórica puede trabajar con su fuente.
- La capa de snapshots queda preparada para ese servidor.
- La documentación backend refleja el nuevo servidor.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 7 archivos modificados o creados.
- Preferir menos de 260 líneas cambiadas.

## Outcome
- Se añadió `comunidad-hispana-03` como tercera fuente histórica estable en el seed declarativo de `historical_servers`, con `scoreboard_base_url` `https://scoreboard.comunidadhll.es:3443` y `server_number` `3`.
- La validación local de `list_historical_servers()` confirma que el backend ya registra `3` servidores históricos.
- La validación local de `build_historical_server_snapshots(server_key='comunidad-hispana-03')` devuelve el lote esperado de `6` snapshots, dejando preparada la capa para ingesta, persistencia y consumo posterior aunque la UI aún no se haya ampliado en esta task.
- Se actualizó la documentación backend y de dominio para reflejar la nueva fuente histórica.
