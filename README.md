# P2Pool Web Monitor

⚡ Live-updating P2Pool dashboard from local data  
📊 Workers, hashrate, shares, charts  
🐳 Docker-first setup, ready in minutes

P2Pool Web Monitor is a lightweight dashboard for local P2Pool nodes.
It reads local P2Pool data, serves a static web UI, and keeps it updated through a shared `data.json` payload.

## Highlights

- ⚙️ Local P2Pool data only
- 🔄 Live updates without full page reload
- 👷 Worker lifecycle tracking: `online`, `recently offline`, `offline`
- 📈 Historical charts for hashrate and shares
- 🔗 Sidechain-aware observer links for `main`, `mini`, `nano`
- 🐳 Full Docker stack included

## Quickstart

Enter the Docker folder:

```bash
cd docker
```

Copy the example env file:

```bash
cp .env.example .env
```

Edit `.env` and set at least:

```bash
P2POOL_WALLET=YOUR_WALLET_HERE
```

Start the stack:

```bash
docker compose up -d --build
```

## Open

Dashboard:

```text
http://<host>:<WEB_PORT>/
```

Live payload:

```text
http://<host>:<WEB_PORT>/data.json
```

## Project Layout

- `docker/` - deploy-ready Docker stack
- `src/` - monitor generator and dashboard templates
- `tests/` - unit and regression tests
- `execution/verify_live_coherence.py` - live consistency checker

## Notes

- Default Docker output is `index.html`
- The dashboard uses `data.json` as its single source of truth
- No external runtime API is required for dashboard data

## Disclaimer

- ⚠️ This project is provided **as-is**, without warranties of any kind.
- 🧪 Use it at your **own risk** and validate outputs before relying on them in production.
- 🤖 This codebase was developed with significant **AI assistance**.
