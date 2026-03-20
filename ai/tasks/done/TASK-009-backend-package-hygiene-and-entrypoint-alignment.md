# TASK-009-backend-package-hygiene-and-entrypoint-alignment

## Goal
Corregir y alinear la estructura mínima del paquete backend en Python para HLL Vietnam, asegurando que el paquete, los imports y el entrypoint real sean consistentes, legibles y mantenibles.

## Context
El backend bootstrap y el esqueleto API placeholder ya existen, pero en resúmenes recientes aparece una posible inconsistencia con el archivo de paquete Python (`init.py` frente a `__init__.py`). Antes de continuar con más ajustes o integrar consumo desde frontend, es importante dejar la base del paquete limpia y sin ambigüedades.

## Steps
1. Revisar la estructura actual de `backend/app/`.
2. Confirmar si el archivo correcto del paquete existe como:
   - `backend/app/__init__.py`
3. Si existe cualquier inconsistencia de naming o packaging, corregirla.
4. Revisar y alinear los imports internos del backend para que sean coherentes con la estructura final.
5. Confirmar cuál es el entrypoint real del backend y dejarlo claro en la documentación.
6. Revisar el comando de arranque documentado y adaptarlo si fuera necesario.
7. Validar que los endpoints placeholder actuales siguen funcionando tras el ajuste.
8. Mantener el cambio pequeño y centrado en higiene estructural, no en nuevas funcionalidades.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- backend/README.md
- backend/requirements.txt
- backend/app/__init__.py
- backend/app/main.py
- backend/app/routes.py
- backend/app/payloads.py

## Expected Files to Modify
- backend/app/__init__.py
- backend/app/main.py
- backend/app/routes.py
- backend/README.md
- opcionalmente otros archivos internos del backend si son estrictamente necesarios para alinear imports y entrypoint

## Constraints
- No añadir integraciones reales.
- No introducir dependencias nuevas innecesarias.
- No tocar frontend.
- No añadir base de datos.
- No hacer cambios destructivos fuera del alcance del paquete backend.
- Mantener el backend simple y consistente con la fase actual.

## Validation
- Existe un archivo de paquete Python correcto en `backend/app/__init__.py`.
- No quedan referencias ambiguas o incorrectas al package layout.
- El entrypoint del backend está claro.
- Los endpoints placeholder actuales siguen respondiendo.
- La documentación del backend refleja el estado real.

## Change Budget
- Preferir menos de 5 archivos modificados.
- Preferir menos de 160 líneas cambiadas.
