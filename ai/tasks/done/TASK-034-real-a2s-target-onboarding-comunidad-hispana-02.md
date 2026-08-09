# TASK-034-real-a2s-target-onboarding-comunidad-hispana-02

## Goal
Dar de alta el segundo target A2S real verificado del proyecto, correspondiente a Comunidad Hispana #02, integrándolo en la configuración del backend de forma clara, mantenible y coherente con el target real ya existente de Comunidad Hispana #01.

## Context
El backend ya tiene onboarding real de Comunidad Hispana #01 y se ha validado la separación entre `game_port` y `query_port`. Ahora también se ha verificado un segundo servidor real:
- Comunidad Hispana #02
- Host/IP: `152.114.195.150`
- Game Port: `7877`
- Query Port: `7878`

La task debe incorporarlo correctamente a la configuración sin introducir ambigüedades entre puertos ni mezclarlo con fuentes no verificadas.

## Steps
1. Revisar la configuración actual de targets A2S.
2. Añadir Comunidad Hispana #02 con:
   - nombre amigable claro
   - host/IP: `152.114.195.150`
   - query port: `7878`
   - game port: `7877`
   - contexto o etiqueta coherente con el proyecto
3. Mantener la configuración desacoplada y limpia.
4. Documentar el alta del nuevo target en el backend.
5. Verificar que el target anterior (#01) sigue correcto y sin regresiones.
6. Mantener el cambio acotado a onboarding de target real.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- backend/README.md
- backend/app/config.py
- backend/app/server_targets.py
- backend/app/collector.py
- backend/app/a2s_client.py

## Expected Files to Modify
- backend/README.md
- backend/app/server_targets.py
- backend/app/config.py
- opcionalmente backend/app/collector.py si necesita una alineación menor

## Constraints
- No tocar frontend.
- No añadir targets no verificados.
- No confundir `game_port` con `query_port`.
- No añadir scraping.
- No hacer cambios destructivos.
- Mantener la configuración simple y clara.

## Validation
- El backend contiene el target real de Comunidad Hispana #02 correctamente registrado.
- El query port configurado es `7878`.
- El game port registrado es `7877`.
- La documentación deja claro cómo está definido este target.
- No se ha roto el target existente de Comunidad Hispana #01.

## Change Budget
- Preferir menos de 4 archivos modificados.
- Preferir menos de 140 líneas cambiadas.
## Outcome
- `backend/app/server_targets.py` registra `Comunidad Hispana #02` junto a `#01` con `host`, `query_port`, `game_port` y `external_server_id` verificados.
- `backend/README.md` documenta ambos targets reales por defecto y mantiene separada la semantica de `query_port` frente a `game_port`.
- No fue necesario tocar `backend/app/config.py` ni `backend/app/collector.py` porque la configuracion existente ya consume el registro de forma desacoplada.

## Validation Result
- Ejecutado desde `backend/`: `python -c "from app.server_targets import load_a2s_targets; print([(t.name, t.host, t.query_port, t.game_port, t.external_server_id) for t in load_a2s_targets()])"`.
- Resultado: el registro carga `Comunidad Hispana #01` y `Comunidad Hispana #02` con `query_port=7778/7878` y `game_port=7777/7877` respectivamente.

## Decision Notes
- Se mantiene un unico `source_name` para la misma familia de servidores reales porque la distincion operativa ya queda en `external_server_id`, host y puertos.
