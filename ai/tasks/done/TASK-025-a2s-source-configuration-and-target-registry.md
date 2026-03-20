# TASK-025-a2s-source-configuration-and-target-registry

## Goal
Definir y preparar una configuración limpia para registrar servidores objetivo de prueba consultables por A2S, de forma que el backend pueda trabajar con una lista controlada de targets sin acoplarse a valores hardcodeados.

## Context
Una vez que exista un cliente A2S mínimo, el proyecto necesita una manera clara de declarar qué servidores de HLL actual se usarán como fuentes de prueba. Esta task debe dejar preparada una configuración o registro simple de targets A2S, reutilizable por el colector y fácil de adaptar en desarrollo.

## Steps
1. Revisar la configuración actual del backend.
2. Definir una forma clara de registrar targets A2S de prueba, incluyendo al menos:
   - nombre amigable
   - host o IP
   - query port
   - contexto o etiqueta de fuente
3. Mantener el diseño desacoplado del resto del backend y fácil de ampliar.
4. Permitir que el colector lea esa configuración sin depender de valores hardcodeados dentro de la lógica principal.
5. Documentar cómo añadir, quitar o modificar servidores de prueba en entorno local.
6. Mantener el alcance en configuración y registro de targets, no en analítica avanzada.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- docs/current-hll-data-ingestion-plan.md
- backend/README.md
- backend/app/config.py
- backend/app/collector.py
- backend/app/storage.py
- backend/app/a2s_client.py si ya existe por la task anterior

## Expected Files to Modify
- backend/README.md
- backend/app/config.py
- backend/app/collector.py
- opcionalmente archivos nuevos dentro de backend/app/ si mejoran claridad, por ejemplo:
  - backend/app/server_targets.py

## Constraints
- No tocar frontend.
- No introducir infraestructura compleja.
- No añadir dependencias innecesarias.
- No hacer cambios destructivos.
- Mantener la configuración simple y orientada a pruebas.

## Validation
- El backend dispone de una lista configurable de targets A2S.
- El colector puede leer esos targets sin depender de constantes dispersas.
- La documentación deja claro cómo configurar servidores de prueba.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 180 líneas cambiadas.

## Outcome
- Se anadio `backend/app/server_targets.py` con un registro pequeno de targets A2S y una carga desacoplada en forma de dataclass.
- `backend/app/config.py` ahora soporta `HLL_BACKEND_A2S_TARGETS` para sobrescribir la lista con un array JSON en desarrollo local.
- `backend/app/collector.py` puede resolver los targets configurados mediante `fetch_configured_a2s_probes()` sin depender de valores hardcodeados en su logica principal.
- `backend/README.md` documenta la ubicacion del registro y como anadir, quitar o modificar targets de prueba.

## Validation Result
- Ejecutado: `python -m compileall backend/app`
- Resultado: compilacion correcta de los modulos del backend.
- Ejecutado: `python -c "from app.server_targets import load_a2s_targets; print(load_a2s_targets())"`
- Resultado: el registro carga el target por defecto con la estructura esperada.

## Decision Notes
- Se eligio JSON en variable de entorno para mantener el override simple, local y sin introducir un nuevo formato de configuracion ni dependencias externas.
