# TASK-095-restore-community-scores-link-and-source-aware-ui

## Goal
Restaurar correctamente el enlace/botón hacia los scores/histórico de comunidad y asegurar que la UI no pierda acciones útiles por depender de mapas hardcodeados incompletos.

## Context
Se ha detectado que el botón/enlace hacia los scores/histórico de comunidad ha desaparecido o se degrada en algunos casos.
La lógica actual depende de un mapa hardcodeado incompleto y no cubre bien todos los servidores o casos reales.

## Steps
1. Auditar:
   - `frontend/index.html`
   - `frontend/assets/js/main.js`
   - `frontend/assets/css/styles.css`
   - si hace falta, el payload backend consumido por `/api/servers`
2. Restaurar el CTA de scores/histórico para todos los servidores relevantes.
3. Evitar depender exclusivamente de un mapa hardcodeado incompleto cuando haya información backend utilizable.
4. Mantener una experiencia estable:
   - si existe URL conocida -> mostrar enlace
   - si no existe -> degradar de forma clara, no desaparecer silenciosamente
5. Mantener el diseño coherente con la landing actual.
6. No mezclar esta task con refactors amplios no relacionados.

## Constraints
- No rehacer toda la homepage.
- No tocar la UI histórico V1/V2 salvo necesidad estricta.
- No inventar enlaces falsos.
- Si una URL no está disponible, la UI debe indicarlo de forma limpia.

## Validation
- El botón/enlace a scores/histórico vuelve a mostrarse correctamente.
- No desaparece por un mapa hardcodeado incompleto.
- La landing sigue renderizando bien.
- La repo queda consistente.

## Expected Files
- `frontend/index.html`
- `frontend/assets/js/main.js`
- `frontend/assets/css/styles.css`
- opcionalmente backend si se necesita exponer mejor la URL o metadata correspondiente
