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

## Basic Configuration

### Wallet

Set your Monero wallet in the `p2pool-mini` command:

```yaml
--wallet REPLACE_WITH_YOUR_MONERO_WALLET
```

### Dashboard Port

The dashboard is exposed on host port `3380` by default:

```yaml
ports:
  - "3380:80"
```

If port `3380` is already used, change only the left side. For example:

```yaml
ports:
  - "8080:80"
```

### Mining Ports

P2Pool exposes these host ports by default:

```yaml
ports:
  - "35443:3333"
  - "37888:37888"
```

If a host port is already used, change only the left side and keep the container port unchanged.

### Sidechain

The default compose runs P2Pool mini:

```yaml
--mini
```

For P2Pool nano, replace `--mini` with:

```yaml
--nano
```

For main P2Pool, remove sidechain flags such as `--mini` or `--nano`.

## Advanced Configuration

The default compose is intentionally simple. Advanced users can still override monitor internals with environment variables.

Monitor path and server overrides:

- `P2POOL_DIR`, default `/p2pool-data`
- `DATA_API_DIR`, default `/p2pool-data`
- `OUTPUT`, default `/output/index.html`
- `HTTP_PORT`, default `8080`

Worker lifecycle overrides:

- `WORKER_RECENTLY_OFFLINE_SECONDS`, default `900`
- `WORKER_RETENTION_SECONDS`, default `86400`

With the default worker settings, a worker becomes `recently offline` after 15 minutes without activity and remains visible for 24 hours before being pruned.

To override these values, add an `environment` block to the `p2pool-wm` service:

```yaml
services:
  p2pool-wm:
    environment:
      WORKER_RECENTLY_OFFLINE_SECONDS: "900"
      WORKER_RETENTION_SECONDS: "86400"
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
