# TASK-061-frontend-dockerization

## Goal
Preparar el frontend estático del proyecto para ejecutarse dentro de un contenedor Docker de forma simple y estable, con una estrategia clara para servir `historico.html`, la landing y los assets.

## Context
El frontend actual es estático y ya funciona localmente, pero aún no tiene una imagen Docker formal para ejecución consistente. Hace falta dejarlo empaquetado de forma simple, sin introducir complejidad innecesaria.

## Steps
1. Revisar la estructura actual del frontend.
2. Diseñar un Dockerfile adecuado para servir el frontend estático.
3. Elegir una estrategia simple y mantenible para servir:
   - `index.html`
   - `historico.html`
   - assets CSS/JS/img
4. Asegurar que el frontend pueda configurarse para hablar con el backend containerizado si hay alguna URL/base path que deba quedar clara.
5. Preparar una estrategia razonable de `.dockerignore` si procede.
6. No introducir frameworks ni bundlers nuevos.
7. No resolver todavía reverse proxy final ni TLS en esta task.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- frontend/index.html
- frontend/historico.html
- frontend/assets/js/main.js
- frontend/assets/js/historico.js
- frontend/assets/css/styles.css
- frontend/assets/css/historico.css
- .gitignore

## Expected Files to Modify
- frontend/Dockerfile
- frontend/.dockerignore
- opcionalmente una mínima documentación asociada si ayuda a explicar el arranque
- opcionalmente un archivo de configuración simple si mejora claridad del servido estático

## Constraints
- No romper el frontend local actual.
- No introducir frameworks nuevos.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en containerizar el frontend estático.

## Validation
- Existe un Dockerfile de frontend funcional.
- El frontend puede servirse correctamente desde contenedor.
- La landing y la página histórica quedan accesibles.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 4 archivos modificados o creados.
- Preferir menos de 180 líneas cambiadas.
