# Technical Decisions

## Decision 001: frontend simple HTML/CSS/JS

Se adopta una base estática con HTML, CSS y JavaScript puro para priorizar simplicidad, velocidad de arranque y compatibilidad total al abrir el frontend directamente en navegador.

## Decision 002: backend previsto en Python

La estructura del repositorio reserva desde el inicio una carpeta de backend porque la implementación futura se realizará en Python.

## Decision 003: estructura preparada para orquestación por agentes

Se incluye una carpeta `ai/` y un documento `AGENTS.md` para facilitar una futura organización del trabajo por roles, tareas y orquestación.

## Decision 004: branding militar Vietnam

La dirección visual inicial se alinea con una estética sobria, táctica y militar inspirada en el contexto Vietnam para mantener coherencia temática desde la primera iteración.

## Decision 005: AI Development Platform integrada de forma adaptada

Se integra una capa de orquestación por tasks inspirada en la plantilla de AI Development Platform, pero adaptada al contexto real de HLL Vietnam y sin arrastrar supuestos genéricos de otros stacks. La plataforma se usa como soporte operativo del repositorio, no como funcionalidad del producto.
