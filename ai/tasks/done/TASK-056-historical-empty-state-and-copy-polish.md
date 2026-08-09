# TASK-056-historical-empty-state-and-copy-polish

## Goal
Mejorar los estados vacíos y el copy de la página histórica para que `comunidad-hispana-03` se muestre de forma honesta mientras no tenga bootstrap ejecutado, y para que la información de cobertura y fallback semanal suene más natural y menos técnica.

## Context
Tras los últimos cambios, la página histórica ya funciona para #01 y #02, pero aún hay aspectos de UX/copy mejorables:
- `comunidad-hispana-03` aparece vacía, lo cual ahora mismo es normal porque no se ha ejecutado bootstrap para ese servidor
- algunos textos siguen sonando demasiado técnicos
- labels como `672,1 días registrados` no son la mejor forma de presentar cobertura histórica
- el texto del fallback semanal es correcto, pero demasiado largo y técnico

## Steps
1. Revisar los textos actuales de:
   - resumen
   - badges de cobertura
   - periodo registrado
   - fallback semanal
   - estados vacíos de resumen / tops / recientes
2. Hacer que `comunidad-hispana-03` muestre un estado explícito y honesto del tipo:
   - sin histórico registrado todavía
   - pendiente de bootstrap / pendiente de registro histórico
   - o equivalente mejor, siempre claro y natural
3. Evitar que `#03` parezca un error roto si simplemente aún no se ha cargado histórico.
4. Revisar la forma de mostrar la cobertura histórica. Priorizar formulaciones más naturales como:
   - cobertura histórica
   - desde X hasta Y
   - periodo registrado
   sobre expresiones demasiado técnicas o poco naturales como el número decimal de días aislado.
5. Simplificar el texto del fallback semanal para que comunique:
   - que se está mostrando la última semana cerrada
   - porque la semana actual aún no tiene suficiente actividad
   sin meter demasiado detalle técnico en el bloque principal
6. Mantener la estética actual de la página histórica.
7. No cambiar la lógica de negocio más allá de lo necesario para mostrar estados/copy correctos.
8. No crear páginas nuevas.
9. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- frontend/historico.html
- frontend/assets/js/historico.js
- frontend/assets/css/historico.css
- backend/app/payloads.py
- backend/README.md

## Expected Files to Modify
- frontend/historico.html
- frontend/assets/js/historico.js
- frontend/assets/css/historico.css
- opcionalmente backend/app/payloads.py si hace falta ajustar labels o metadatos presentables
- opcionalmente backend/README.md si el comportamiento visible cambia y conviene dejarlo documentado

## Constraints
- No romper la UI histórica que ya funciona para #01 y #02.
- No convertir esta task en un rediseño grande.
- No introducir frameworks nuevos.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en estados vacíos y copy.

## Validation
- `#03` deja de parecer un fallo ambiguo y muestra un estado vacío claro y honesto.
- La cobertura histórica se presenta de forma más natural.
- El texto del fallback semanal se entiende mejor.
- La UI sigue siendo coherente con la landing y con el resto de la página histórica.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados.
- Preferir menos de 220 líneas cambiadas.
