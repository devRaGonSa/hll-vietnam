# JTA Docker Compose Deploy

Este despliegue prepara una variante directa para JTA sin Portainer y sin tocar
la logica funcional del proyecto.

## Archivos

- `docker-compose.yml`: stack directo para JTA
- `.env.example`: plantilla de variables sin credenciales reales
- `backups/`: carpeta local para dumps `.dump` o `.sql`

## Preparacion

1. Copia la plantilla:

   ```powershell
   Copy-Item deploy/jta/.env.example deploy/jta/.env
   ```

2. Ajusta como minimo:

- `POSTGRES_PASSWORD`
- `HLL_BACKEND_RCON_TARGETS`
- `FRONTEND_BACKEND_BASE_URL`
- `HLL_BACKEND_ALLOWED_ORIGINS`

Notas:

- `HLL_BACKEND_RCON_TARGETS` debe ser un JSON valido en una sola linea.
- en `.env` conviene dejar ese JSON entre comillas simples para preservar los espacios
- `HLL_DB_MAINTENANCE_ENABLED=false` queda desactivado por defecto.
- `FRONTEND_BACKEND_BASE_URL` debe apuntar a la URL que vera el navegador.
  Ejemplo remoto: `http://IP_O_DOMINIO_JTA:8000`.
- `HLL_BACKEND_ALLOWED_ORIGINS` debe incluir la URL publica del frontend.
  Ejemplo remoto: `http://IP_O_DOMINIO_JTA:8080`.

## Arranque

Desde la raiz del repo:

```powershell
docker compose -f deploy/jta/docker-compose.yml --env-file deploy/jta/.env up -d --build
```

Alternativa equivalente desde `deploy/jta`:

```powershell
cd deploy/jta
docker compose --env-file .env up -d --build
```

Ambas funcionan porque los contextos de build y los bind mounts se resuelven
relativos a `deploy/jta/docker-compose.yml`.

## Arranque Con Workers Advanced

Desde raiz:

```powershell
docker compose -f deploy/jta/docker-compose.yml --env-file deploy/jta/.env --profile advanced up -d --build
```

Desde `deploy/jta`:

```powershell
docker compose --env-file .env --profile advanced up -d --build
```

Servicios:

- normales: `postgres`, `backend`, `frontend`
- perfil `advanced`: `historical-runner`, `rcon-historical-worker`

## Parada

Parada sin borrar datos:

```powershell
docker compose -f deploy/jta/docker-compose.yml --env-file deploy/jta/.env down
```

Advertencia:

- no usar `docker compose down -v`
- no borrar el volumen `jta-postgres-data`

## Backup Y Restore

Esta task no ejecuta backup ni restore real. Los comandos siguientes son solo
runbook operativo.

### 1. Crear dump desde el PostgreSQL actual

Ejemplo usando el contenedor PostgreSQL actual:

```powershell
docker exec -t hll-vietnam-postgres pg_dump -U hll_vietnam -d hll_vietnam -Fc -f /tmp/hll_vietnam_jta.dump
docker cp hll-vietnam-postgres:/tmp/hll_vietnam_jta.dump .\hll_vietnam_jta.dump
Copy-Item .\hll_vietnam_jta.dump deploy\jta\backups\
```

Si el nombre del contenedor actual es distinto, sustituirlo por el real.

### 2. Levantar solo PostgreSQL en JTA

```powershell
docker compose -f deploy/jta/docker-compose.yml --env-file deploy/jta/.env up -d postgres
```

### 3. Restaurar dump en JTA

Con el dump ya copiado a `deploy/jta/backups/`:

```powershell
docker compose -f deploy/jta/docker-compose.yml --env-file deploy/jta/.env exec postgres sh -c "pg_restore --clean --if-exists -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" /backups/hll_vietnam_jta.dump"
```

## Validacion De Datos Tras Restore

Comprobar tablas clave:

```powershell
docker compose -f deploy/jta/docker-compose.yml --env-file deploy/jta/.env exec postgres sh -c "psql -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" -c 'select count(*) from rcon_materialized_matches;'"
docker compose -f deploy/jta/docker-compose.yml --env-file deploy/jta/.env exec postgres sh -c "psql -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" -c 'select count(*) from rcon_admin_log_events;'"
docker compose -f deploy/jta/docker-compose.yml --env-file deploy/jta/.env exec postgres sh -c "psql -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" -c 'select count(*) from displayed_historical_snapshots;'"
```

## Endpoints A Probar

- frontend: `http://IP_O_DOMINIO_JTA:8080`
- backend health: `http://IP_O_DOMINIO_JTA:8000/health`
- `http://IP_O_DOMINIO_JTA:8000/api/servers`
- `http://IP_O_DOMINIO_JTA:8000/api/historical/server-summary?server=comunidad-hispana-01`
- `http://IP_O_DOMINIO_JTA:8000/api/historical/recent-matches?limit=20&server=comunidad-hispana-01`

## Logs A Revisar

Basicos:

```powershell
docker compose -f deploy/jta/docker-compose.yml --env-file deploy/jta/.env logs --tail=200 postgres backend frontend
```

Advanced:

```powershell
docker compose -f deploy/jta/docker-compose.yml --env-file deploy/jta/.env logs --tail=200 historical-runner rcon-historical-worker
```

Eventos utiles a buscar:

- `database-maintenance-scheduler-*`
- `historical-refresh-*`
- `database-maintenance-*`
- errores de conexion RCON

## Validacion Del Compose

La plantilla incluida usa valores de ejemplo sintacticamente validos, incluido
el JSON de `HLL_BACKEND_RCON_TARGETS`, para permitir:

```powershell
docker compose -f deploy/jta/docker-compose.yml --env-file deploy/jta/.env.example config
```
