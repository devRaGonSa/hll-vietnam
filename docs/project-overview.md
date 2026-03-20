# Project Overview

## Vision del proyecto

HLL Vietnam busca convertirse en la base de una web de comunidad para centralizar la presencia digital de una comunidad hispana alrededor del juego, con una identidad visual sobria, tactica y coherente con el universo Vietnam.

## Objetivo inicial

Publicar una landing simple que permita presentar la comunidad, mostrar el trailer del proyecto y facilitar el acceso directo al servidor de Discord.

## Alcance actual

- Estructura inicial del repositorio.
- Landing estatica en HTML, CSS y JavaScript.
- Documentacion base para organizar el crecimiento del proyecto.
- Preparacion de carpetas para backend y orquestacion futura.
- Plataforma de tasks y orquestacion integrada para coordinar trabajo tecnico.

## Stack actual

- HTML
- CSS
- JavaScript
- Git para control de versiones

## Stack futuro previsto

- Backend principal en Python
- Integraciones de comunidad y automatizacion
- Posible ampliacion de paneles administrativos y servicios internos

## Contrato inicial frontend backend

El repositorio define un contrato API inicial en `docs/frontend-backend-contract.md` para alinear la futura comunicacion entre la landing y el backend Python.

En esta fase solo existe `GET /health` como endpoint implementado. Las rutas de comunidad, trailer, Discord y servidores quedan documentadas como contrato previsto para futuras tasks sin cambiar todavia el comportamiento visible del frontend.

## Evolucion prevista del frontend

La landing debe seguir siendo funcional al abrirse directamente en navegador mientras los datos dinamicos se introducen de forma incremental. La estrategia de consumo prevista usa `fetch` y JavaScript simple cuando una task lo requiera, siempre conservando fallbacks estaticos mientras se valida cada endpoint.

La planificacion detallada de prioridades de consumo, estados de carga, errores y placeholders queda en `docs/frontend-data-consumption-plan.md`.
