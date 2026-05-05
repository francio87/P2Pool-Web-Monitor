# Source Notes

`p2pool_web_monitor.py` is the CLI entry point for generating dashboard data from local P2Pool files.

## Runtime Inputs

- `P2POOL_DIR` or `--p2pool-dir`: local P2Pool directory candidate
- `DATA_API_DIR` or `--data-api-dir`: explicit P2Pool data-api directory
- `OUTPUT` or `--output`: output HTML file or output directory

## Docker Defaults

The published container defaults to:

- `P2POOL_DIR=/p2pool-data`
- `DATA_API_DIR=/p2pool-data`
- `OUTPUT=/output/index.html`
- `HTTP_PORT=8080`

The entrypoint performs an initial `--once` generation check, starts continuous generation, and serves `/output` with Python's static HTTP server for direct `docker run` use.

## Output Files

- HTML dashboard: derived from `OUTPUT`
- Live payload: `data.json` alongside the HTML file
- History state: `history.json` alongside the HTML file

The Docker image uses `index.html` so web servers can serve the dashboard at `/` without additional routing.

## Worker Lifecycle Settings

The application supports two optional environment overrides:

- `WORKER_RECENTLY_OFFLINE_SECONDS`, default `900`
- `WORKER_RETENTION_SECONDS`, default `86400`

These values are intentionally omitted from the default compose file because the defaults match the recommended behavior. They can be added to the `p2pool-wm` service environment when an operator wants custom retention timing.
