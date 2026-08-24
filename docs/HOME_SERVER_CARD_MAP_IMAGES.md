# Imágenes de mapas en las tarjetas de Inicio

Las miniaturas HLL reutilizan los WebP locales de `frontend/assets/img/maps/`,
procedentes del catálogo instalado de CRCON. El resolver central
`frontend/assets/js/map-image-resolver.js` normaliza acentos, espacios, IDs de
capa, aliases de nombre y variantes de entorno antes de elegir el asset.

La auditoría de CRCON 12.0.1 identifica seis mapas HLL Vietnam mediante los IDs
estables `wdeva`–`wdevf`. Sus imágenes dedicadas no están presentes en el
proyecto, el host ni los contenedores actuales. Esos IDs y nombres quedan
registrados en el resolver, pero usan `unknown-day.webp` hasta que exista un
asset local verificado. No se hacen hotlinks ni se sustituye un mapa por otro.

Las tarjetas no realizan consultas por servidor: reutilizan el único payload
`/api/servers`, que ya proyecta desde CRCON `get_public_info` los jugadores, el
mapa, el score de los lados estables 1/2 y `remaining_match_time_seconds`. En
HLL esos lados corresponden a Allies/Axis; en HLL Vietnam, a South/North. El
frontend conserva ese orden y solo anima localmente el tiempo entre refrescos.
