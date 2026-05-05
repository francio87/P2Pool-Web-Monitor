# P2Pool Web Monitor

⚡ Live-updating P2Pool dashboard from local data  
📊 Workers, hashrate, shares, charts  
🐳 Docker-first setup, ready in minutes

P2Pool Web Monitor is a lightweight dashboard for local P2Pool nodes.
It reads P2Pool `--data-api` files, writes a static web root, and keeps it updated through a shared `data.json` payload.

## Highlights

- ⚙️ Local P2Pool data only
- 🔄 Live updates without full page reload
- 👷 Worker lifecycle tracking: `online`, `recently offline`, `offline`
- 📈 Historical charts for hashrate and shares
- 🔗 Sidechain-aware observer links for `main`, `mini`, `nano`
- 🐳 Full Docker stack included

## Quickstart

Edit `docker-compose.yml` and replace the wallet placeholder:

```yaml
--wallet REPLACE_WITH_YOUR_MONERO_WALLET
```

Start the full stack:

```bash
docker compose up -d
```

The default stack starts P2Pool mini, P2Pool Web Monitor, and nginx.
No `.env` file and no local Docker build are required.

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

## Advanced Configuration

The default compose is intentionally simple. Advanced users can still override monitor internals with environment variables:

- `P2POOL_DIR`
- `DATA_API_DIR`
- `OUTPUT`
- `HTTP_PORT`
- `WORKER_RECENTLY_OFFLINE_SECONDS`
- `WORKER_RETENTION_SECONDS`

## Worker Retention

Default worker lifecycle timings:

- `WORKER_RECENTLY_OFFLINE_SECONDS=900`
- `WORKER_RETENTION_SECONDS=86400`

This means a worker becomes `recently offline` after 15 minutes without activity and remains visible for 24 hours before being pruned.

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
docker build -t ghcr.io/francio87/p2pool-web-monitor:dev .
```

## Project Layout

- `Dockerfile` - image for `p2pool-wm`
- `docker-compose.yml` - all-in-one stack with P2Pool, monitor, and nginx
- `src/` - monitor generator and dashboard templates

## Notes

- Default Docker output is `index.html`
- The dashboard uses `data.json` as its single source of truth
- No external runtime API is required for dashboard data

## Disclaimer

- ⚠️ This project is provided **as-is**, without warranties of any kind.
- 🧪 Use it at your **own risk** and validate outputs before relying on them in production.
- 🤖 This codebase was developed with significant **AI assistance**.
