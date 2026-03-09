from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from pathlib import Path

from monitor_common import (
    DEFAULT_HISTORY_BUCKET_SECONDS,
    DEFAULT_HISTORY_RETENTION_SECONDS,
    DEFAULT_REFRESH_SECONDS,
    format_hashrate,
    format_number,
    format_time_ago,
    format_unix_datetime,
    format_xmr,
    get_observer_base_url,
    normalize_sidechain_mode,
    truncate_wallet,
)
from monitor_workers import normalize_workers_for_render


def build_render_data(data: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    render_data_source = dict(data)
    render_data_source["workers"] = normalize_workers_for_render(data.get("workers", []))
    reliability = data.get("reliability", {}) if isinstance(data.get("reliability"), dict) else {}

    return {
        "data": render_data_source,
        "history": {
            "labels": [entry.get("label", "") for entry in history],
            "hr15m": [entry.get("h15_avg", 0) for entry in history],
            "hr1h": [entry.get("h1_avg", 0) for entry in history],
            "shares": [entry.get("shares_delta", 0) for entry in history],
        },
        "meta": {
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "refresh_seconds": DEFAULT_REFRESH_SECONDS,
            "history_window_hours": max(1, DEFAULT_HISTORY_RETENTION_SECONDS // 3600),
            "history_bucket_minutes": max(1, DEFAULT_HISTORY_BUCKET_SECONDS // 60),
            "worker_recently_offline_seconds": reliability.get("worker_recently_offline_seconds", 0),
            "worker_retention_seconds": reliability.get("worker_retention_seconds", 0),
        },
        "format": {
            "hashrate_15m": format_hashrate(render_data_source["stratum"].get("hashrate_15m", 0)),
            "hashrate_1h": format_hashrate(render_data_source["stratum"].get("hashrate_1h", 0)),
            "hashrate_24h": format_hashrate(render_data_source["stratum"].get("hashrate_24h", 0)),
            "shares_found": format_number(render_data_source["stratum"].get("shares_found", 0)),
            "shares_failed": format_number(render_data_source["stratum"].get("shares_failed", 0)),
            "wallet_short": truncate_wallet(render_data_source["stratum"].get("wallet", "")),
            "sidechain_mode": normalize_sidechain_mode(render_data_source["stratum"].get("sidechain_mode")),
            "observer_base_url": get_observer_base_url(render_data_source["stratum"].get("sidechain_mode")),
            "last_share_ago": format_time_ago(render_data_source["stratum"].get("last_share_found_time", 0)),
            "pool_hashrate": format_hashrate(render_data_source["pool"].get("pool_statistics", {}).get("hashRate", 0)),
            "network_reward": format_xmr(render_data_source["network"].get("reward", 0)),
            "public_peers": format_number(render_data_source["peers"].get("public_count", 0)),
            "onion_peers": format_number(render_data_source["peers"].get("onion_count", 0)),
            "freshness_log": format_unix_datetime(render_data_source["freshness"].get("p2pool_log_ts", 0)),
            "freshness_stratum": format_unix_datetime(render_data_source["freshness"].get("stratum_ts", 0)),
            "freshness_p2p": format_unix_datetime(render_data_source["freshness"].get("p2p_ts", 0)),
            "freshness_pool": format_unix_datetime(render_data_source["freshness"].get("pool_stats_ts", 0)),
            "freshness_network": format_unix_datetime(render_data_source["freshness"].get("network_stats_ts", 0)),
            "reliability_reasons": reliability.get("reasons", []),
            "not_enough_data": bool(reliability.get("not_enough_data", False)),
        },
    }
def render_json(output_path: Path, payload: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=True), encoding="utf-8")
    tmp_path.replace(output_path)


def print_verbose_summary(data: dict[str, Any]) -> None:
    print("\n--- Recap of extracted information ---")
    print(f"Status:         {data.get('status', 'Disconnected')}")
    print(f"Uptime:         {data.get('p2p', {}).get('uptime_str', 'Unknown')}")
    workers = data.get("workers", [])
    print(f"Workers:        {len(workers)} active")
    for worker in workers:
        if isinstance(worker, dict):
            name = worker.get("name") or worker.get("id") or "Worker"
            address = worker.get("remote_address", "N/A")
            rate = format_hashrate(worker.get("hashrate_current", worker.get("hashrate", 0)))
            print(f"  - {name} ({address}): {rate}")

    pool_stats = data.get("pool", {}).get("pool_statistics", {})
    print(f"Pool Hashrate:  {format_hashrate(pool_stats.get('hashRate', 0))}")
    print(f"Network Height: {data.get('network', {}).get('height', 'N/A')}")
    print(f"Monero Node:    {data.get('p2p', {}).get('monero_node', 'N/A')}")
    print(f"Wallet:         {data.get('stratum', {}).get('wallet', 'Unknown')}")
    print(f"Shares Found:   {data.get('stratum', {}).get('shares_found', 0)}")
    print(f"Shares Failed:  {data.get('stratum', {}).get('shares_failed', 0)}")

    peers = data.get("peers", {})
    print("\nPeers:")
    print(f"  Public list:  {peers.get('public_count', 0)}")
    print(f"  Onion list:   {peers.get('onion_count', 0)}")

    freshness = data.get("freshness", {})
    print("\nData Freshness:")
    print(f"  p2pool log:   {format_unix_datetime(int(freshness.get('p2pool_log_ts', 0) or 0))}")
    print(f"  local/stratum:{format_unix_datetime(int(freshness.get('stratum_ts', 0) or 0))}")
    print(f"  local/p2p:    {format_unix_datetime(int(freshness.get('p2p_ts', 0) or 0))}")
    print(f"  pool/stats:   {format_unix_datetime(int(freshness.get('pool_stats_ts', 0) or 0))}")
    print(f"  network/stats:{format_unix_datetime(int(freshness.get('network_stats_ts', 0) or 0))}")

    sources = data.get("sources", {})
    print("\nSources:")
    print(f"  Network:      {sources.get('network', 'N/A')}")
    print(f"  Pool:         {sources.get('pool', 'N/A')}")
    print(f"  Peers:        {sources.get('peers', 'N/A')}")
    print(f"  Stratum/P2P:  {sources.get('stratum_p2p', 'N/A')}")

    reliability = data.get("reliability", {})
    if isinstance(reliability, dict):
        print("\nReliability:")
        print(f"  Not enough:   {bool(reliability.get('not_enough_data', False))}")
        print(f"  Reasons:      {', '.join(reliability.get('reasons', [])) or 'none'}")
    print("---------------------------------------")
