# TASK-028-real-a2s-target-onboarding

## Goal
Dar de alta el primer target A2S real verificado del proyecto, correspondiente a Comunidad Hispana #01, integrandolo en la configuracion del backend de forma clara, mantenible y documentada.

## Context
El backend ya dispone de cliente A2S, registro configurable de targets y colector integrado con persistencia. Ademas, ya se ha identificado un target real consultable por A2S:
- Comunidad Hispana #01
- Host/IP: 152.114.195.174
- Query Port: 7778
- Game Port: 7777

El objetivo de esta task es incorporar ese target real a la configuracion del proyecto sin asumir otros servidores aun no verificados.

## Steps
1. Revisar la configuracion actual de targets A2S del backend.
2. Anadir el target real verificado de Comunidad Hispana #01 usando:
   - nombre amigable claro
   - host/IP: `152.114.195.174`
   - query port: `7778`
   - etiqueta o contexto de fuente coherente con el proyecto
3. Asegurar que la configuracion no dependa de valores hardcodeados dispersos fuera del registro o capa configurada.
4. Mantener separada la nocion de query port y game port para evitar confusiones.
5. Reflejar en la documentacion del backend como esta registrado este primer target real.
6. Dejar claro en documentacion que Comunidad Hispana #02 no debe anadirse aun sin confirmar su query port real.
7. Mantener el cambio pequeno y estrictamente centrado en onboarding de target.

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
- backend/app/config.py
- backend/app/server_targets.py
- opcionalmente backend/app/collector.py si necesita alineacion menor para consumir el target de forma limpia

## Constraints
- No tocar frontend.
- No introducir nuevos targets no verificados.
- No asumir datos de Comunidad Hispana #02.
- No anadir scraping.
- No hacer cambios destructivos.
- Mantener la configuracion simple y clara.

## Validation
- El backend contiene el target real de Comunidad Hispana #01 correctamente registrado.
- El query port configurado es `7778`.
- La documentacion deja claro como esta definido este target.
- No se han introducido targets inciertos o ambiguos.

## Change Budget
- Preferir menos de 4 archivos modificados.
- Preferir menos de 140 lineas cambiadas.

## Outcome
- `backend/app/server_targets.py` registra por defecto solo `Comunidad Hispana #01` con `host` real, `query_port` verificado y `game_port` separado como dato opcional de referencia.
- `backend/app/config.py` centraliza el `source_name` por defecto para evitar valores dispersos en el registro A2S.
- `backend/README.md` documenta el target real incorporado y deja explicito que Comunidad Hispana #02 no debe anadirse hasta confirmar su `query_port`.

## Validation Result
- Ejecutado desde `backend/`: `python -` importando `load_a2s_targets()`.
- Resultado: el registro carga `Comunidad Hispana #01` con `host=152.114.195.174`, `query_port=7778`, `game_port=7777` y `source_name=community-hispana-a2s`.

## Decision Notes
- Se mantiene `game_port` fuera de la logica de consulta A2S y solo como metadato opcional del target para evitar confundirlo con `query_port`.
