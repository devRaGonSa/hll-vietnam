# TASK-060-backend-dockerization

## Goal
Preparar el backend Python del proyecto para ejecutarse correctamente dentro de un contenedor Docker, con una imagen reproducible, variables de entorno claras y persistencia adecuada de datos históricos y snapshots.

## Context
El backend ya funciona localmente, pero aún no está preparado formalmente para una ejecución containerizada estándar. Antes de pensar en despliegue real, hace falta empaquetarlo de forma consistente y dejar claro cómo se inyectan configuración, rutas de datos y puertos.

## Steps
1. Revisar la estructura actual del backend y su forma de arranque.
2. Diseñar un Dockerfile específico para el backend.
3. Asegurar que el backend pueda arrancar en contenedor con:
   - host correcto
   - puerto configurable
   - variables de entorno ya soportadas por el proyecto
4. Revisar qué rutas del backend deben persistirse fuera del contenedor, especialmente:
   - SQLite histórica
   - snapshots JSON
   - cualquier artefacto operativo relevante
5. Preparar una estrategia razonable de `.dockerignore` para backend.
6. Mantener la imagen lo más simple y reproducible posible.
7. No resolver todavía reverse proxy final ni TLS en esta task.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/main.py
- backend/app/config.py
- backend/app/historical_ingestion.py
- backend/app/historical_runner.py
- backend/app/historical_snapshots.py
- backend/requirements.txt
- .gitignore

## Expected Files to Modify
- backend/Dockerfile
- backend/.dockerignore
- backend/README.md
- opcionalmente archivos de entorno de ejemplo si mejoran claridad, por ejemplo:
  - backend/.env.example

## Constraints
- No romper el arranque local existente.
- No eliminar la persistencia local del histórico.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en containerizar el backend.

## Validation
- Existe un Dockerfile de backend funcional.
- La persistencia necesaria del backend queda identificada y documentada.
- El backend puede ejecutarse con configuración inyectable por entorno.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
