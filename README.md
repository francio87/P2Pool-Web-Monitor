# P2Pool Web Monitor

Live-updating P2Pool dashboard from local P2Pool data.

P2Pool Web Monitor reads P2Pool `--data-api` files, generates a static dashboard, and keeps a shared `data.json` payload updated for live in-page refreshes.

## Highlights

- Local P2Pool data only
- Live updates without a backend API
- Worker lifecycle tracking: `online`, `recently offline`, `offline`
- Historical charts for hashrate and shares
- Sidechain-aware observer links for `main`, `mini`, `nano`
- Docker-first all-in-one stack

## Quickstart

Download the compose file or clone this repository, then edit the wallet placeholder in `docker-compose.yml`:

```yaml
--wallet REPLACE_WITH_YOUR_MONERO_WALLET
```

Start the full stack:

```bash
docker compose up -d
```

The default compose starts:

- `p2pool-mini` from `ghcr.io/sethforprivacy/p2pool:latest`
- `p2pool-wm` from `ghcr.io/francio87/p2pool-web-monitor:latest`
- `web` from `nginx:1.27-alpine`

No `.env` file is required for the default Docker Compose setup.

## Open

Dashboard:

```text
http://<host>:3380/
```

Live payload:

```text
http://<host>:3380/data.json
```

Mining ports exposed by default:

- Stratum: `35443`
- P2P: `37888`

## Docker Run

If you already have P2Pool data available on the host, you can run only the monitor image:

```bash
docker run -d \
  --name p2pool-wm \
  --restart unless-stopped \
  -p 3380:8080 \
  -v /path/to/p2pool:/p2pool-data:ro \
  ghcr.io/francio87/p2pool-web-monitor:latest
```

The image generates `/output/index.html` and `/output/data.json`, then serves `/output` on container port `8080`.

## GHCR Publishing

This repository includes `.github/workflows/docker-publish.yml`.

On pushes to `main`, GitHub Actions publishes:

- `ghcr.io/francio87/p2pool-web-monitor:latest`
- `ghcr.io/francio87/p2pool-web-monitor:stable`
- `ghcr.io/francio87/p2pool-web-monitor:<short-sha>`

On pushes to `dev`, it publishes:

- `ghcr.io/francio87/p2pool-web-monitor:dev`
- `ghcr.io/francio87/p2pool-web-monitor:<short-sha>`

On tags such as `v1.0.0`, it also publishes versioned tags.

To test the development image with the all-in-one stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

After the first successful workflow run, make the GitHub package public from the package settings if GitHub creates it as private.

## Advanced Configuration

The default compose is intentionally explicit and avoids required `.env` files.

Advanced users can still override monitor internals with environment variables supported by the container:

- `P2POOL_DIR`
- `DATA_API_DIR`
- `OUTPUT`
- `HTTP_PORT`
- `WORKER_RECENTLY_OFFLINE_SECONDS`
- `WORKER_RETENTION_SECONDS`

## Advanced Worker Retention

Worker lifecycle timing defaults are built into the application:

- `WORKER_RECENTLY_OFFLINE_SECONDS=900`
- `WORKER_RETENTION_SECONDS=86400`

With these defaults, a worker becomes `recently offline` after 15 minutes without activity and remains visible for 24 hours before being pruned.

To override these values, add an `environment` block to the `p2pool-wm` service:

```yaml
services:
  p2pool-wm:
    environment:
      WORKER_RECENTLY_OFFLINE_SECONDS: "900"
      WORKER_RETENTION_SECONDS: "86400"
```

## Verify

From the repository root:

```bash
docker compose config -q
docker compose -f docker-compose.yml -f docker-compose.dev.yml config -q
docker build -t ghcr.io/francio87/p2pool-web-monitor:dev .
```

## Project Layout

- `Dockerfile` - image for `p2pool-wm`
- `docker-compose.yml` - all-in-one stack with P2Pool, monitor, and nginx
- `docker-compose.dev.yml` - optional override for the GHCR `dev` image
- `.github/workflows/docker-publish.yml` - GHCR publishing workflow
- `src/` - monitor generator and dashboard templates

## Notes

- Docker output is `/output/index.html`
- The dashboard uses `data.json` as its single source of truth
- No external runtime API is required for dashboard data

## Disclaimer

- This project is provided as-is, without warranties of any kind.
- Use it at your own risk and validate outputs before relying on them in production.
