# NAS / Portainer deployment

This deployment path is for the Proxmox NAS Docker/Portainer environment. It keeps the development `docker-compose.yml` unchanged and adds a production compose file under `deploy/portainer/`.

## Files

- `deploy/portainer/docker-compose.nas.yml`: production compose for Portainer.
- `deploy/portainer/stack.env.example`: safe environment template. Copy values into Portainer and replace placeholders.
- `deploy/portainer/Caddyfile.example`: Caddy reverse proxy block for `comunidadhll.devzamode.es`.

## Portainer stack

1. In Portainer, create a new Stack from the cloned repository.
2. Use compose file path:

   ```text
   deploy/portainer/docker-compose.nas.yml
   ```

3. Paste variables from `deploy/portainer/stack.env.example` into the stack environment editor.
4. Replace all placeholders, especially:
   - `POSTGRES_PASSWORD`
   - `HLL_BACKEND_DATABASE_URL`
   - `HLL_BACKEND_RCON_TARGETS`

The production compose does not publish host ports. Caddy is the only public entrypoint. Backend and frontend are attached to the external Docker network configured by `CADDY_NETWORK`, defaulting to `stack-caddy`.

## External Caddy network

Make sure the Caddy network exists:

```bash
docker network ls | grep stack-caddy
```

If the network does not exist, create it from the Caddy stack or manually:

```bash
docker network create stack-caddy
```

## Caddy configuration

Add this block to `/mnt/data8tb/NAS/stack-caddy/Caddyfile`:

```caddyfile
comunidadhll.devzamode.es {
    encode zstd gzip

    reverse_proxy /health hll-vietnam-backend-1:8000
    reverse_proxy /api/* hll-vietnam-backend-1:8000

    reverse_proxy hll-vietnam-frontend-1:8080
}
```

Then format and reload Caddy:

```bash
docker exec caddy caddy fmt --overwrite /etc/caddy/Caddyfile
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

## Verification

From the NAS or another machine:

```bash
curl -I https://comunidadhll.devzamode.es
curl https://comunidadhll.devzamode.es/health
curl https://comunidadhll.devzamode.es/api/servers
```

In Portainer, check logs for:

- backend
- frontend
- postgres

With Docker CLI:

```bash
docker compose -f deploy/portainer/docker-compose.nas.yml ps
docker compose -f deploy/portainer/docker-compose.nas.yml logs --tail=100 backend
docker compose -f deploy/portainer/docker-compose.nas.yml logs --tail=100 frontend
```

## Updating after git pull

From the repository directory on the NAS:

```bash
git pull origin main
docker compose -f deploy/portainer/docker-compose.nas.yml build
docker compose -f deploy/portainer/docker-compose.nas.yml up -d
```

Or redeploy the stack from Portainer.

## Advanced historical workers

Normal production startup includes only:

- postgres
- backend
- frontend

Historical workers are opt-in through the `advanced` profile:

```bash
docker compose -f deploy/portainer/docker-compose.nas.yml --profile advanced up -d historical-runner rcon-historical-worker
```

Stop them before running manual backfills or other long writer jobs:

```bash
docker compose -f deploy/portainer/docker-compose.nas.yml --profile advanced stop historical-runner rcon-historical-worker
```

## Local validation commands

Run from repository root:

```bash
docker compose config
docker compose -f deploy/portainer/docker-compose.nas.yml config
docker compose -f deploy/portainer/docker-compose.nas.yml build
```

The development compose still exposes local ports for `http://localhost:8080` and `http://localhost:8000`. The NAS compose intentionally exposes no host ports.
