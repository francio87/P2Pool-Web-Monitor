#!/bin/sh
set -eu

MAX_AGE="${P2POOL_HEALTH_MAX_AGE:-300}"
BASE_DIR="${P2POOL_HEALTH_DIR:-/home/p2pool}"
NOW=$(date +%s)

fresh() {
  path="$1"
  test -s "$path" || exit 1
  mt=$(stat -c %Y "$path" 2>/dev/null || echo 0)
  age=$((NOW - mt))
  test "$age" -le "$MAX_AGE"
}

positive() {
  grep -Eq "\"$2\"[[:space:]]*:[[:space:]]*[1-9][0-9]*" "$1"
}

listen() {
  port_hex="$1"
  grep -Eq ":${port_hex}[[:space:]].*[[:space:]]0A[[:space:]]" /proc/net/tcp /proc/net/tcp6 2>/dev/null
}

fresh "$BASE_DIR/local/p2p"
fresh "$BASE_DIR/pool/stats"
fresh "$BASE_DIR/network/stats"
positive "$BASE_DIR/local/p2p" peer_list_size
positive "$BASE_DIR/local/p2p" connections
positive "$BASE_DIR/pool/stats" sidechainHeight
positive "$BASE_DIR/pool/stats" sidechainDifficulty
positive "$BASE_DIR/network/stats" height
positive "$BASE_DIR/network/stats" difficulty
listen 0D05
listen 9400
