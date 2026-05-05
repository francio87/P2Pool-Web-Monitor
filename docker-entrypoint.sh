#!/bin/sh
set -eu

: "${P2POOL_DIR:=/p2pool-data}"
: "${DATA_API_DIR:=/p2pool-data}"
: "${OUTPUT:=/output/index.html}"
: "${HTTP_PORT:=8080}"

OUTPUT_DIR=$(dirname "$OUTPUT")
mkdir -p "$OUTPUT_DIR"

cp -f /app/src/templates/p2pool_web_monitor.html "$OUTPUT"
cp -f /app/src/templates/chart.umd.min.js "$OUTPUT_DIR/chart.umd.min.js"
cp -f /app/src/templates/inter-regular.ttf "$OUTPUT_DIR/inter-regular.ttf"
cp -f /app/src/templates/favicon.svg "$OUTPUT_DIR/favicon.svg"
cp -f /app/src/templates/favicon.ico "$OUTPUT_DIR/favicon.ico"

python3 src/p2pool_web_monitor.py --p2pool-dir "$P2POOL_DIR" --data-api-dir "$DATA_API_DIR" --output "$OUTPUT" --once
python3 src/p2pool_web_monitor.py --p2pool-dir "$P2POOL_DIR" --data-api-dir "$DATA_API_DIR" --output "$OUTPUT" &

exec python3 -m http.server "$HTTP_PORT" --directory "$OUTPUT_DIR"
