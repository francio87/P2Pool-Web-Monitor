#!/bin/sh
set -eu

: "${P2POOL_DIR:=/p2pool-data}"
: "${DATA_API_DIR:=/p2pool-data}"
: "${OUTPUT:=/output/index.html}"
: "${HTTP_PORT:=8080}"
: "${P2POOL_VERSION_CHECK:=true}"

OUTPUT_DIR=$(dirname "$OUTPUT")
mkdir -p "$OUTPUT_DIR"

cp -f /app/src/templates/p2pool_web_monitor.html "$OUTPUT"
cp -f /app/src/templates/chart.umd.min.js "$OUTPUT_DIR/chart.umd.min.js"
cp -f /app/src/templates/inter-regular.ttf "$OUTPUT_DIR/inter-regular.ttf"
cp -f /app/src/templates/favicon.svg "$OUTPUT_DIR/favicon.svg"
cp -f /app/src/templates/favicon.ico "$OUTPUT_DIR/favicon.ico"

python3 src/p2pool_web_monitor.py --p2pool-dir "$P2POOL_DIR" --data-api-dir "$DATA_API_DIR" --output "$OUTPUT" --once

python3 src/p2pool_web_monitor.py --p2pool-dir "$P2POOL_DIR" --data-api-dir "$DATA_API_DIR" --output "$OUTPUT" &
MONITOR_PID=$!

python3 -m http.server "$HTTP_PORT" --directory "$OUTPUT_DIR" &
HTTP_PID=$!

shutdown() {
  kill "$MONITOR_PID" "$HTTP_PID" 2>/dev/null || true
}

trap 'shutdown' TERM INT HUP

while kill -0 "$MONITOR_PID" 2>/dev/null && kill -0 "$HTTP_PID" 2>/dev/null; do
  sleep 1
done

STATUS=0
if ! kill -0 "$MONITOR_PID" 2>/dev/null; then
  wait "$MONITOR_PID" || STATUS=$?
fi
if ! kill -0 "$HTTP_PID" 2>/dev/null; then
  wait "$HTTP_PID" || STATUS=$?
fi

shutdown
wait "$MONITOR_PID" 2>/dev/null || true
wait "$HTTP_PID" 2>/dev/null || true

exit "$STATUS"
