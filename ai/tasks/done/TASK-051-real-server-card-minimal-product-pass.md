# TASK-051-real-server-card-minimal-product-pass

## Goal
Dejar las tarjetas de servidores reales en una forma minima y orientada a producto final, mostrando solo la informacion esencial para un visitante que quiere ver estado actual y conectarse.

## Context
Las tarjetas ya se simplificaron parcialmente, pero todavia quedaban restos de estructura y bloques secundarios que no aportaban suficiente valor. El objetivo era dejar una tarjeta muy clara y minima, centrada en estado actual del servidor.

## Steps
1. Revisar la composicion actual de las tarjetas reales.
2. Asegurar que el contenido visible principal quede limitado a:
   - nombre
   - estado
   - jugadores
   - mapa
   - region
   - ultima actualizacion
   - boton Conectar
3. Evaluar si promedio y pico deben quedar ocultos o pasar a una capa secundaria muy discreta.
4. Eliminar cualquier bloque residual que complique la lectura rapida.
5. Mejorar la jerarquia para que el usuario vea en pocos segundos si el servidor le interesa.
6. Mantener una composicion limpia y coherente con el ancho actual de la pagina.
7. No tocar backend salvo una alineacion menor si fuera imprescindible.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css
- backend/app/payloads.py

## Expected Files to Modify
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css

## Constraints
- No romper el boton Conectar.
- No eliminar la informacion util esencial.
- No anadir librerias nuevas.
- No hacer cambios destructivos.
- Mantener el ajuste centrado en UX de producto final.

## Validation
- Las tarjetas muestran solo informacion util y clara.
- La lectura es rapida y limpia.
- No quedan bloques residuales de informacion interna o excesiva.
- La UI se siente mas final y menos experimental.

## Change Budget
- Preferir menos de 3 archivos modificados.
- Preferir menos de 140 lineas cambiadas.

## Outcome
- `frontend/assets/js/main.js` deja las tarjetas dinamicas en su forma minima: identidad, estado, jugadores, mapa, region, ultima actualizacion y CTA cuando existe destino conectable.
- `frontend/index.html` alinea las tarjetas estaticas de fallback con esa misma estructura minima.
- `frontend/assets/css/styles.css` elimina estilos de bloques residuales ya innecesarios, como la barra de carga y los encabezados intermedios de seccion, para reforzar una lectura mas rapida.

## Validation Result
- Validado con `node --check frontend/assets/js/main.js`.
- Verificado con `rg` que ya no quedan restos de `server-card__load`, `server-panel-section`, ni texto asociado a metricas o bloques historicos secundarios dentro de `frontend/`.
- Revisado en diff: la task queda limitada a `frontend/index.html`, `frontend/assets/js/main.js`, `frontend/assets/css/styles.css` y este archivo de task.

## Decision Notes
- Se elimino la barra visual de ocupacion porque duplicaba la informacion ya expresada por `Jugadores` y cargaba la tarjeta sin mejorar la decision principal del visitante.
