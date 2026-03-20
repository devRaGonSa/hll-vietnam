# Frontend Data Consumption Plan

## Objective

Definir como evolucionara la landing de HLL Vietnam desde contenido estatico hacia bloques alimentados por el backend sin romper simplicidad, branding ni compatibilidad al abrir `frontend/index.html` directamente.

## Current Frontend Blocks With Future Dynamic Potential

- Hero principal: titulo, resumen y CTA de Discord podran leer `community` y `discord`.
- Bloque de trailer: podra leer `trailer` para desacoplar video y titulo del HTML.
- Estado de servidores: queda reservado para una futura seccion y no debe forzarse en la landing actual.

## Recommended Consumption Strategy

- Usar `fetch` nativo cuando una task habilite consumo real.
- Mantener JavaScript simple en `frontend/assets/js/main.js` o dividir en modulos ligeros solo si el numero de bloques dinamicos ya lo justifica.
- Centralizar la URL base del backend en una configuracion minima si el frontend deja de ser puramente estatico en un entorno concreto.
- No llamar a servicios externos desde el navegador; el frontend debe hablar con el backend Python.

## UI State Rules

### Loading

- No bloquear el render inicial de la landing.
- Mostrar skeletons o placeholders ligeros solo en bloques futuros que ya dependan del backend.

### Error

- Si falla una llamada, conservar el contenido estatico existente o un mensaje tactico breve y no intrusivo.
- Registrar el error en consola durante desarrollo sin degradar toda la pagina.

### Empty state

- Si `servers.items` llega vacio, mostrar un estado neutral de "informacion disponible mas adelante".
- Si un bloque opcional no tiene datos, ocultarlo o dejar un placeholder discreto en lugar de mostrar errores tecnicos.

### Fallback

- Mantener el Discord CTA hardcoded hasta que `/api/discord` sea estable.
- Mantener el iframe del trailer fijo hasta validar `/api/trailer`.
- No hacer depender el hero de `/health`.

## Endpoint Priority

1. `/api/community`
2. `/api/trailer`
3. `/api/discord`
4. `/api/servers`
5. `/health` solo para checks tecnicos o diagnostico en desarrollo

## Progressive Migration Path

### Step 1

- Introducir una capa minima de lectura para `community` y `trailer`.
- Reutilizar el HTML actual como fallback.

### Step 2

- Sustituir el CTA de Discord por datos de `/api/discord` cuando el placeholder backend sea estable.
- Mantener la URL actual como respaldo local.

### Step 3

- Anadir una seccion de servidores solo cuando exista diseno, contrato y placeholder suficientemente claros.
- Evitar reservar complejidad en la landing antes de que ese bloque aporte valor real.

## Explicitly Out Of Scope Now

- Implementar `fetch` real.
- Cambiar el comportamiento visible de la landing.
- Introducir librerias de estado o frameworks frontend.
- Conectar el navegador directamente con Discord o con APIs de servidores.
