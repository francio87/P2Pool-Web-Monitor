#!/bin/sh
set -eu

HTML_DIR="${NGINX_HEALTH_HTML_DIR:-/usr/share/nginx/html}"
MAX_AGE="${NGINX_HEALTH_MAX_AGE:-120}"
DATA_JSON="$HTML_DIR/data.json"
INDEX_HTML="$HTML_DIR/index.html"

test -s "$DATA_JSON"
test -s "$INDEX_HTML"
age=$(($(date +%s) - $(stat -c %Y "$DATA_JSON")))
test "$age" -le "$MAX_AGE"
grep -q '"meta"' "$DATA_JSON"
wget -q -O - http://127.0.0.1/ | grep -q 'P2Pool'
wget -q -O - http://127.0.0.1/data.json | grep -q '"meta"'
