from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from monitor_common import (
    LOG_HEAD_SCAN_BYTES,
    LOG_TAIL_SCAN_BYTES,
    STALE_THRESHOLDS_SECONDS,
    deep_copy_default_results,
    format_duration_seconds,
    normalize_sidechain_mode,
    parse_int,
    parse_uptime_to_seconds,
    resolve_worker_recently_offline_seconds,
    resolve_worker_retention_seconds,
    to_hashrate,
)
from monitor_paths import (
    count_nonempty_lines,
    get_mtime_unix,
    load_json_file,
    resolve_data_api_dir,
    resolve_required_log_path,
    safe_relative,
)
from monitor_workers import build_worker_record, parse_workers_from_api, reconcile_workers


RE_WORKER_LINE = re.compile(
    r"StratumServer\s+([^\s]+)\s+(yes|no)\s+(.*?)\s+(\d+)\s+([\d.]+)\s+([kMGT]?H/s)\s+(.*)"
)
RE_HASHRATE = re.compile(r"=\s+([\d.]+)\s+([kMGT]?H/s)")
RE_INT_VALUE = re.compile(r"=\s+(\d+)")
RE_TEXT_VALUE = re.compile(r"=\s+(.*)")
RE_MONERO_NODE = re.compile(r"=\s+([^\s:]+):RPC\s+(\d+)")
RE_MINER_HOST = re.compile(r"host\s*=\s*([^\s:]+):RPC\s+(\d+)")
RE_SIDECHAIN_POOL_NAME = re.compile(r"(?:SideChain\s+)?pool name\s*=\s*(.+)$", re.IGNORECASE)


def deep_merge(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_merge(target[key], value)
        else:
            target[key] = value


def compute_reliability(data: dict[str, Any], now_ts: int) -> dict[str, Any]:
    freshness = data.get("freshness", {}) if isinstance(data.get("freshness"), dict) else {}
    ages = {
        "stratum": max(0, now_ts - parse_int(str(freshness.get("stratum_ts", 0)), 0)),
        "pool": max(0, now_ts - parse_int(str(freshness.get("pool_stats_ts", 0)), 0)),
        "network": max(0, now_ts - parse_int(str(freshness.get("network_stats_ts", 0)), 0)),
        "p2p": max(0, now_ts - parse_int(str(freshness.get("p2p_ts", 0)), 0)),
        "log": max(0, now_ts - parse_int(str(freshness.get("p2pool_log_ts", 0)), 0)),
    }

    stale_sources: dict[str, bool] = {}
    reasons: list[str] = []
    for source, age in ages.items():
        stale = age > STALE_THRESHOLDS_SECONDS[source]
        stale_sources[source] = stale
        if stale:
            reasons.append(f"stale_{source}")

    stratum = data.get("stratum", {}) if isinstance(data.get("stratum"), dict) else {}
    pool_stats = data.get("pool", {}).get("pool_statistics", {}) if isinstance(data.get("pool"), dict) else {}
    network = data.get("network", {}) if isinstance(data.get("network"), dict) else {}
    workers = data.get("workers", []) if isinstance(data.get("workers"), list) else []

    if not stratum:
        reasons.append("missing_stratum_api")
    if not pool_stats:
        reasons.append("missing_pool_api")
    if not network:
        reasons.append("missing_network_api")
    if parse_int(str(stratum.get("total_stratum_shares", 0)), 0) <= 0:
        reasons.append("warming_up")
    if not [w for w in workers if isinstance(w, dict) and w.get("status") == "online"]:
        reasons.append("no_active_workers")

    not_enough = any(reason in reasons for reason in (
        "missing_stratum_api",
        "missing_pool_api",
        "missing_network_api",
        "stale_stratum",
        "stale_pool",
    ))

    return {
        "not_enough_data": not_enough,
        "reasons": sorted(set(reasons)),
        "stale_sources": stale_sources,
        "source_ages_seconds": ages,
        "worker_recently_offline_seconds": resolve_worker_recently_offline_seconds(),
        "worker_retention_seconds": resolve_worker_retention_seconds(),
    }


def parse_workers_from_log(lines: list[str]) -> list[dict[str, Any]]:
    workers: list[dict[str, Any]] = []
    total_index = next((idx for idx in range(len(lines) - 1, -1, -1) if "StratumServer Total:" in lines[idx]), -1)
    if total_index < 0:
        return workers

    j = total_index - 1
    while j >= 0:
        candidate = lines[j]
        if "StratumServer" not in candidate or "IP:port" in candidate:
            break
        match = RE_WORKER_LINE.search(candidate)
        if match:
            rate = to_hashrate(float(match.group(5)), match.group(6))
            worker_name = match.group(7).strip() or "Worker"
            workers.append(
                build_worker_record(
                    name=worker_name,
                    remote_address=match.group(1),
                    difficulty=int(match.group(4)),
                    shares_found=0,
                    hashrate=rate,
                    hashrate_1h=rate,
                    hashrate_current=rate,
                    hashrate_data_fresh=True,
                    status="online",
                )
            )
        j -= 1
    workers.reverse()
    return workers


def _find_last_index(lines: list[str], marker: str) -> int:
    for idx in range(len(lines) - 1, -1, -1):
        if marker in lines[idx]:
            return idx
    return -1


def _parse_context(lines: list[str], marker_index: int, before: int, after: int) -> list[str]:
    if marker_index < 0:
        return []
    start = max(0, marker_index - before)
    end = min(len(lines), marker_index + after + 1)
    return lines[start:end]


def _read_log_tail(log_path: Path, size_bytes: int) -> str:
    try:
        with log_path.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - size_bytes))
            return handle.read().decode("utf-8", errors="ignore")
    except OSError:
        return ""


def _read_log_head(log_path: Path, size_bytes: int) -> str:
    try:
        with log_path.open("rb") as handle:
            return handle.read(size_bytes).decode("utf-8", errors="ignore")
    except OSError:
        return ""


def _extract_sidechain_mode_from_lines(lines: list[str], reverse: bool = False) -> str:
    iterable = reversed(lines) if reverse else lines
    for sample in iterable:
        pool_name_match = RE_SIDECHAIN_POOL_NAME.search(sample)
        if pool_name_match:
            return normalize_sidechain_mode(pool_name_match.group(1))
    return "unknown"


def parse_status_blocks(lines: list[str], results: dict[str, Any]) -> None:
    stratum = results["stratum"]
    pool_stats = results["pool"]["pool_statistics"]
    p2p = results["p2p"]

    for sample in _parse_context(lines, _find_last_index(lines, "StratumServer status"), 20, 20):
        if "Hashrate (15m est)" in sample:
            match = RE_HASHRATE.search(sample)
            if match and not float(stratum.get("hashrate_15m", 0) or 0):
                stratum["hashrate_15m"] = to_hashrate(float(match.group(1)), match.group(2))
        elif "Hashrate (1h  est)" in sample:
            match = RE_HASHRATE.search(sample)
            if match and not float(stratum.get("hashrate_1h", 0) or 0):
                stratum["hashrate_1h"] = to_hashrate(float(match.group(1)), match.group(2))
        elif "P2Pool shares found" in sample:
            match = RE_INT_VALUE.search(sample)
            if match and not parse_int(str(stratum.get("shares_found", 0)), 0):
                stratum["shares_found"] = int(match.group(1))
        elif "P2Pool shares failed" in sample:
            match = RE_INT_VALUE.search(sample)
            if match and not parse_int(str(stratum.get("shares_failed", 0)), 0):
                stratum["shares_failed"] = int(match.group(1))

    for sample in _parse_context(lines, _find_last_index(lines, "SideChain status"), 20, 20):
        pool_name_match = RE_SIDECHAIN_POOL_NAME.search(sample)
        if pool_name_match:
            results["stratum"]["sidechain_mode"] = normalize_sidechain_mode(pool_name_match.group(1))
        if "Monero node" in sample:
            match = RE_MONERO_NODE.search(sample)
            if match:
                results["p2p"]["monero_node"] = f"{match.group(1)}:{match.group(2)}"
            else:
                fallback = RE_TEXT_VALUE.search(sample)
                if fallback:
                    results["p2p"]["monero_node"] = fallback.group(1).strip()
        elif "Your wallet address" in sample:
            match = RE_TEXT_VALUE.search(sample)
            if match:
                results["stratum"]["wallet"] = match.group(1).strip()
        elif "Side chain hashrate" in sample:
            match = RE_HASHRATE.search(sample)
            if match and not float(pool_stats.get("hashRate", 0) or 0):
                pool_stats["hashRate"] = to_hashrate(float(match.group(1)), match.group(2))

    for sample in _parse_context(lines, _find_last_index(lines, "P2PServer status"), 12, 12):
        if "Uptime" in sample:
            match = RE_TEXT_VALUE.search(sample)
            if match and not str(p2p.get("uptime_str", "") or "").strip():
                uptime = match.group(1).strip()
                p2p["uptime_str"] = uptime
                p2p["uptime"] = parse_uptime_to_seconds(uptime)
        elif "Connections" in sample:
            match = RE_INT_VALUE.search(sample)
            if match and not parse_int(str(p2p.get("connections", 0)), 0):
                connections = int(match.group(1))
                p2p["connections"] = connections
                stratum["connections"] = connections
        elif "Peer list size" in sample:
            match = RE_INT_VALUE.search(sample)
            if match and not parse_int(str(p2p.get("peer_list_size", 0)), 0):
                p2p["peer_list_size"] = int(match.group(1))


def parse_log_file(log_path: Path, results: dict[str, Any]) -> None:
    if not log_path.exists():
        return
    tail = _read_log_tail(log_path, LOG_TAIL_SCAN_BYTES)
    if not tail:
        return
    lines = tail.splitlines()
    workers = parse_workers_from_log(lines)
    if workers and not results.get("workers"):
        results["workers"] = workers
        results["stratum"]["workers"] = workers
    parse_status_blocks(lines, results)

    if normalize_sidechain_mode(results.get("stratum", {}).get("sidechain_mode")) == "unknown":
        results["stratum"]["sidechain_mode"] = _extract_sidechain_mode_from_lines(lines, reverse=True)
    if normalize_sidechain_mode(results.get("stratum", {}).get("sidechain_mode")) == "unknown":
        head = _read_log_head(log_path, LOG_HEAD_SCAN_BYTES)
        results["stratum"]["sidechain_mode"] = _extract_sidechain_mode_from_lines(head.splitlines())

    current_node = str(results.get("p2p", {}).get("monero_node", "") or "").strip().lower()
    if current_node in {"", "unknown"}:
        for sample in reversed(lines):
            if "host" not in sample or ":RPC" not in sample:
                continue
            match = RE_MINER_HOST.search(sample)
            if match:
                results["p2p"]["monero_node"] = f"{match.group(1)}:{match.group(2)}"
                break


def fetch_p2pool_data_from_disk(
    base_dir: str,
    data_api_dir: str | None = None,
    worker_state: dict[str, dict[str, Any]] | None = None,
    now_ts: int | None = None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    base = Path(base_dir)
    timestamp_now = now_ts if now_ts is not None else int(time.time())
    state = worker_state or {}
    result = deep_copy_default_results()
    result["status"] = "Connected"
    log_path = resolve_required_log_path(base)
    worker_recently_offline_seconds = resolve_worker_recently_offline_seconds()
    worker_retention_seconds = resolve_worker_retention_seconds()

    api_base = resolve_data_api_dir(base, data_api_dir)
    if api_base is not None:
        result["sources"]["data_api"] = safe_relative(api_base, base)
        pool_stats_path = api_base / "pool" / "stats"
        network_stats_path = api_base / "network" / "stats"
        stratum_path = api_base / "local" / "stratum"
        p2p_path = api_base / "local" / "p2p"

        deep_merge(result["pool"], load_json_file(pool_stats_path))
        deep_merge(result["network"], load_json_file(network_stats_path))
        deep_merge(result["stratum"], load_json_file(stratum_path))
        deep_merge(result["p2p"], load_json_file(p2p_path))

        result["freshness"]["pool_stats_ts"] = get_mtime_unix(pool_stats_path)
        result["freshness"]["network_stats_ts"] = get_mtime_unix(network_stats_path)
        result["freshness"]["stratum_ts"] = get_mtime_unix(stratum_path)
        result["freshness"]["p2p_ts"] = get_mtime_unix(p2p_path)

        result["sources"]["pool"] = safe_relative(pool_stats_path, base)
        result["sources"]["network"] = safe_relative(network_stats_path, base)
        result["sources"]["stratum"] = safe_relative(stratum_path, base)
        result["sources"]["p2p"] = safe_relative(p2p_path, base)

    workers_live = parse_workers_from_api(result["stratum"].get("workers", []))
    workers_display, updated_state = reconcile_workers(
        workers_live,
        state,
        timestamp_now,
        worker_recently_offline_seconds,
        worker_retention_seconds,
    )
    result["workers"] = workers_display
    result["stratum"]["workers"] = workers_live

    result["peers"]["public_count"] = count_nonempty_lines(base / "p2pool_peers.txt")
    result["peers"]["onion_count"] = count_nonempty_lines(base / "p2pool_onion_peers.txt")
    result["sources"]["peers"] = "p2pool_peers.txt + p2pool_onion_peers.txt"

    if log_path is not None:
        result["freshness"]["p2pool_log_ts"] = get_mtime_unix(log_path)
        result["sources"]["stratum_p2p"] = str(log_path.relative_to(base))
        parse_log_file(log_path, result)

    p2p_data = result.get("p2p", {}) if isinstance(result.get("p2p"), dict) else {}
    if not str(p2p_data.get("uptime_str", "") or "").strip():
        uptime_seconds = parse_int(str(p2p_data.get("uptime", 0)), 0)
        if uptime_seconds > 0:
            result["p2p"]["uptime_str"] = format_duration_seconds(uptime_seconds)

    result["reliability"] = compute_reliability(result, timestamp_now)
    result["reliability"]["worker_recently_offline_seconds"] = worker_recently_offline_seconds
    result["reliability"]["worker_retention_seconds"] = worker_retention_seconds
    return result, updated_state
