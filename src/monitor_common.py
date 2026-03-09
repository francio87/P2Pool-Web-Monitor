from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_RESULTS: dict[str, Any] = {
    "status": "Disconnected",
    "error": None,
    "stratum": {
        "hashrate_15m": 0.0,
        "hashrate_1h": 0.0,
        "hashrate_24h": 0.0,
        "shares_found": 0,
        "shares_failed": 0,
        "current_effort": 0.0,
        "connections": 0,
        "incoming_connections": 0,
        "block_reward_share_percent": 0.0,
        "last_share_found_time": 0,
        "wallet": "",
        "sidechain_mode": "unknown",
        "workers": [],
    },
    "pool": {
        "pool_statistics": {
            "hashRate": 0.0,
            "miners": 0,
            "totalBlocksFound": 0,
            "pplnsWindowSize": 0,
            "sidechainDifficulty": 0,
            "sidechainHeight": 0,
        }
    },
    "network": {"height": 0, "difficulty": 0, "reward": 0},
    "p2p": {
        "peer_list_size": 0,
        "uptime": 0,
        "uptime_str": "",
        "zmq_last_active": None,
        "connections": 0,
        "monero_node": "Unknown",
    },
    "peers": {
        "public_count": 0,
        "onion_count": 0,
    },
    "freshness": {
        "p2pool_log_ts": 0,
        "stratum_ts": 0,
        "p2p_ts": 0,
        "pool_stats_ts": 0,
        "network_stats_ts": 0,
    },
    "sources": {
        "data_api": "none",
        "stratum": "local/stratum",
        "p2p": "local/p2p",
        "network": "network/stats",
        "pool": "pool/stats",
        "peers": "none",
        "stratum_p2p": "p2pool.log",
    },
    "reliability": {
        "not_enough_data": True,
        "reasons": ["missing_data_api"],
        "stale_sources": {},
        "source_ages_seconds": {},
        "worker_recently_offline_seconds": 900,
        "worker_retention_seconds": 86400,
    },
    "workers": [],
}

REQUIRED_LOG_CANDIDATES = (
    "p2pool.log",
    ".p2pool/p2pool.log",
)
DEFAULT_REFRESH_SECONDS = 30
DEFAULT_HISTORY_BUCKET_SECONDS = 15 * 60
DEFAULT_HISTORY_RETENTION_SECONDS = 24 * 60 * 60
DEFAULT_WORKER_RECENTLY_OFFLINE_SECONDS = 15 * 60
DEFAULT_WORKER_RETENTION_SECONDS = 24 * 60 * 60
STATE_SCHEMA_VERSION = 2

STALE_THRESHOLDS_SECONDS = {
    "stratum": 120,
    "pool": 120,
    "network": 300,
    "p2p": 240,
    "log": 300,
}

LOG_TAIL_SCAN_BYTES = 200_000
LOG_HEAD_SCAN_BYTES = 64_000

SIDECHAIN_OBSERVER_BASE_URLS = {
    "main": "https://p2pool.observer",
    "mini": "https://mini.p2pool.observer",
    "nano": "https://nano.p2pool.observer",
}


def deep_copy_default_results() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_RESULTS))


def normalize_sidechain_mode(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return "unknown"
    if "mini" in raw:
        return "mini"
    if "nano" in raw:
        return "nano"
    if raw in {"main", "mainchain", "p2pool"}:
        return "main"
    return "unknown"


def get_observer_base_url(sidechain_mode: str | None) -> str:
    normalized = normalize_sidechain_mode(sidechain_mode)
    return SIDECHAIN_OBSERVER_BASE_URLS.get(normalized, SIDECHAIN_OBSERVER_BASE_URLS["main"])


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def parse_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_uptime_to_seconds(up_str: str) -> int:
    if not up_str:
        return 0
    total = 0
    for suffix, multiplier in {"d": 86400, "h": 3600, "m": 60, "s": 1}.items():
        match = re.search(rf"(\d+){suffix}", up_str)
        if match:
            total += int(match.group(1)) * multiplier
    return total


def format_duration_seconds(total_seconds: int) -> str:
    total = max(0, int(total_seconds))
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if days or hours:
        parts.append(f"{hours}h")
    if days or hours or minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def _parse_env_seconds(name: str, default: int, minimum: int) -> int:
    configured = os.getenv(name)
    if not configured:
        return default
    try:
        parsed = int(configured)
    except ValueError:
        return default
    return max(minimum, parsed)


def resolve_worker_recently_offline_seconds() -> int:
    return _parse_env_seconds(
        "WORKER_RECENTLY_OFFLINE_SECONDS",
        DEFAULT_WORKER_RECENTLY_OFFLINE_SECONDS,
        60,
    )


def resolve_worker_retention_seconds() -> int:
    return _parse_env_seconds(
        "WORKER_RETENTION_SECONDS",
        DEFAULT_WORKER_RETENTION_SECONDS,
        60,
    )


def to_hashrate(value: float, unit: str) -> float:
    unit_norm = unit.strip().lower()
    if unit_norm.startswith("kh"):
        return value * 1_000
    if unit_norm.startswith("mh"):
        return value * 1_000_000
    if unit_norm.startswith("gh"):
        return value * 1_000_000_000
    if unit_norm.startswith("th"):
        return value * 1_000_000_000_000
    return value


def format_hashrate(value: Any) -> str:
    try:
        hashrate = float(value)
    except (TypeError, ValueError):
        return "0 H/s"
    if hashrate <= 0:
        return "0 H/s"
    units = ["H/s", "KH/s", "MH/s", "GH/s", "TH/s"]
    index = 0
    while hashrate >= 1000 and index < len(units) - 1:
        hashrate /= 1000.0
        index += 1
    if index == 0:
        return f"{int(round(hashrate))} {units[index]}"
    return f"{hashrate:.2f} {units[index]}"


def format_number(value: Any) -> str:
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "-"


def format_xmr(piconero: Any) -> str:
    try:
        return f"{float(piconero) / 1e12:.6f} XMR"
    except (TypeError, ValueError):
        return "-"


def format_time_ago(timestamp: Any) -> str:
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return "Never"
    if ts <= 0:
        return "Never"
    diff = int(time.time()) - ts
    if diff < 0:
        return "Just now"
    if diff < 60:
        return f"{diff}s ago"
    if diff < 3600:
        return f"{diff // 60}m ago"
    if diff < 86400:
        return f"{diff // 3600}h ago"
    return f"{diff // 86400}d ago"


def truncate_wallet(wallet: str) -> str:
    if not wallet:
        return "Reading..."
    if len(wallet) < 20:
        return wallet
    return f"{wallet[:10]}...{wallet[-8:]}"


def format_unix_datetime(timestamp: int) -> str:
    if timestamp <= 0:
        return "Unknown"
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
