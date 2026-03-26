# TASK-110-elo-mmr-accuracy-capabilities-and-product-surface

## Goal
Exponer de forma clara y honesta en payloads y superficie de producto qué parte del sistema Elo/MMR es exacta, cuál es aproximada y cuál no está disponible todavía, alineándolo con el motor V2 y el diseño del PDF.

## Context
El sistema Elo/MMR no solo debe calcularse bien; también debe comunicar bien su grado de exactitud. Ya existe una superficie mínima con metadata de capabilities, pero debe revisarse para quedar alineada con el motor V2 y con la auditoría del gap real frente al PDF.

## Scope
Backend principalmente. Frontend solo si hiciera falta una exposición mínima ya existente y muy localizada.

## Steps
1. Auditar:
   - `backend/app/payloads.py`
   - `backend/app/routes.py`
   - cualquier exposición actual de Elo/MMR
   - el resultado de `TASK-108`
   - el motor ajustado por `TASK-109`
2. Revisar cómo se exponen hoy:
   - `accuracy_mode`
   - `capabilities`
   - ratios exact/approximate/not_available
3. Alinear esa exposición con la realidad del motor V2 y el PDF.
4. Hacer que los payloads expliquen de forma honesta:
   - qué componentes usan señales exactas
   - qué componentes usan proxies
   - qué componentes no pueden calcularse todavía
5. Mantener la salida usable para producto y futura UI, sin sobrecargar innecesariamente la respuesta.
6. Actualizar documentación/runbook si hace falta.

## Constraints
- No afirmar exactitud falsa.
- No mezclar esta task con una gran reescritura visual.
- No romper endpoints existentes.
- Mantener claridad para producto.

## Validation
- Elo/MMR expone metadata de exactitud coherente con el motor real.
- Payloads y documentación reflejan honestamente exact / approximate / not available.
- La repo queda consistente.

## Expected Files
- `backend/app/payloads.py`
- `backend/app/routes.py` si hace falta
- `backend/README.md`
- otros archivos backend solo si son estrictamente necesarios

## Outcome
- Se alineó la exposición de exactitud con el motor Elo/MMR actualizado.
- `backend/app/payloads.py` mantiene los endpoints existentes y añade un bloque
  compacto `accuracy_contract` para:
  - leaderboard Elo/MMR
  - perfil Elo/MMR de jugador
- Ese contrato resume:
  - `accuracy_mode`
  - ratios exact / approximate / not available
  - `component_status` por señal cuando existe metadata de capabilities
- `backend/README.md` se actualizó para reflejar:
  - qué componentes son exactos hoy
  - cuáles siguen siendo proxy
  - qué parte sigue no disponible
  - cómo quedó la alineación V2 del motor y de la superficie de producto
- No hizo falta tocar `routes.py` porque la superficie HTTP ya era suficiente y
  la mejora fue aditiva sobre payloads existentes.

## Validation Notes
- `python -m py_compile backend\\app\\payloads.py`
- `git diff --name-only`
