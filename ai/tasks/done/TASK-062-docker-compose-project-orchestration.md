# TASK-062-docker-compose-project-orchestration

## Goal
Añadir una orquestación básica por Docker Compose para levantar conjuntamente frontend y backend del proyecto con persistencia adecuada del histórico.

## Context
Una vez frontend y backend estén dockerizados, hace falta una forma simple de arrancarlos juntos para desarrollo y predespliegue. Esta task debe dejar una base clara y operativa sin meterse todavía en infraestructura final de producción.

## Steps
1. Revisar los Dockerfile de frontend y backend.
2. Diseñar un `docker-compose.yml` o equivalente moderno para levantar ambos servicios.
3. Asegurar que el backend exponga correctamente su puerto al frontend.
4. Configurar persistencia razonable para:
   - SQLite histórica
   - snapshots JSON
5. Preparar nombres de servicio y red interna claros.
6. Asegurar que el proyecto pueda arrancarse con una instrucción sencilla.
7. No introducir todavía reverse proxy público, TLS ni balanceo.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/Dockerfile
- frontend/Dockerfile
- backend/README.md
- frontend files relevantes
- .gitignore

## Expected Files to Modify
- docker-compose.yml
- backend/README.md
- opcionalmente README raíz si conviene documentar el arranque conjunto
- opcionalmente archivos `.env.example` si mejoran claridad

## Constraints
- No romper el uso local fuera de Docker.
- No meter todavía infraestructura final de producción.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en levantar el proyecto completo con Docker Compose.

## Validation
- Existe una orquestación Docker Compose clara para frontend y backend.
- Los datos persistentes del backend no se pierden al recrear contenedores.
- El proyecto puede levantarse con un flujo simple y documentado.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
