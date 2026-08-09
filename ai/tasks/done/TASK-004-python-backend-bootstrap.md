# TASK-004-python-backend-bootstrap

## Goal
Preparar una base minima y ordenada de backend en Python para el proyecto HLL Vietnam, dejando la estructura lista para crecer sin implementar todavia logica de negocio real ni integraciones externas.

## Context
El proyecto ya dispone de una landing minima funcional y de la capa operativa AI Platform integrada. El siguiente paso tecnico logico es dejar preparado el backend principal del proyecto, que estara basado en Python. En esta fase no se busca desarrollar funcionalidades reales, sino establecer una base limpia, mantenible y coherente con la futura evolucion del sistema.

## Steps
1. Revisar la estructura actual de la carpeta `backend/`.
2. Preparar una base minima de aplicacion Python dentro de `backend/app/`.
3. Crear o ajustar un punto de entrada claro para la aplicacion, por ejemplo un archivo principal como:
   - `backend/app/main.py`
4. Definir una estructura minima coherente para crecimiento posterior.
5. Anadir un endpoint o mecanismo minimo de verificacion de estado, por ejemplo:
   - `/health`
   o equivalente segun la solucion elegida.
6. Actualizar `backend/README.md` para explicar:
   - proposito de la carpeta backend
   - stack elegido en esta fase
   - como arrancar localmente la base minima si ya aplica
7. Ajustar `backend/requirements.txt` con las dependencias minimas reales, si fueran necesarias.
8. Mantener el alcance estricto: solo bootstrap tecnico del backend.

## Files to Read First
- README.md
- AGENTS.md
- docs/project-overview.md
- docs/roadmap.md
- docs/decisions.md
- ai/repo-context.md
- ai/architecture-index.md
- backend/README.md
- backend/requirements.txt
- backend/app/__init__.py

## Expected Files to Modify
- backend/README.md
- backend/requirements.txt
- backend/app/__init__.py
- backend/app/main.py

## Constraints
- No implementar logica de Discord.
- No implementar logica de servidores de juego.
- No anadir base de datos todavia.
- No introducir complejidad innecesaria.
- No tocar frontend salvo documentacion cruzada minima si fuera imprescindible.
- No hacer cambios destructivos.
- Mantener la solucion simple, clara y preparada para crecer.

## Validation
- Existe una estructura backend mas solida que la inicial.
- Existe un punto de entrada claro para la aplicacion Python.
- Existe una verificacion minima de estado o equivalente.
- La documentacion del backend refleja correctamente el nuevo estado.
- No se han anadido funcionalidades fuera de alcance.
- El backend queda listo para que una siguiente task defina contratos API o primeras rutas reales.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 220 lineas cambiadas.

## Outcome
- Bootstrap backend implementado con Python estandar, sin frameworks ni dependencias externas.
- Punto de entrada creado en `backend/app/main.py`.
- Health check minimo disponible en `GET /health`.
- `backend/README.md` actualizado con estructura, alcance y forma de arranque local.
- `backend/requirements.txt` mantenido sin dependencias externas para evitar compromisos prematuros de arquitectura.
