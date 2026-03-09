from __future__ import annotations

from typing import Any


WORKER_FALLBACK_NAME = "Worker"


def parse_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_stripped_text(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def normalize_worker_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def build_worker_record(
    *,
    name: str,
    remote_address: str,
    difficulty: int = 0,
    total_hashes: int = 0,
    last_share_age_seconds: int = 0,
    shares_found: int = 0,
    hashrate: float = 0.0,
    hashrate_1h: float | None = None,
    hashrate_current: float | None = None,
    hashrate_data_fresh: bool = True,
    status: str = "online",
) -> dict[str, Any]:
    resolved_name = _as_stripped_text(name, _as_stripped_text(remote_address, WORKER_FALLBACK_NAME))
    resolved_remote = _as_stripped_text(remote_address, "N/A")
    worker_key = normalize_worker_name(resolved_name) or normalize_worker_name(resolved_remote)
    current_hashrate = hashrate if hashrate_current is None else hashrate_current
    avg_hashrate = hashrate if hashrate_1h is None else hashrate_1h
    return {
        "id": worker_key,
        "worker_key": worker_key,
        "name": resolved_name,
        "remote_address": resolved_remote,
        "difficulty": difficulty,
        "total_hashes": total_hashes,
        "last_share_age_seconds": last_share_age_seconds,
        "shares_found": shares_found,
        "hashrate": hashrate,
        "hashrate_1h": avg_hashrate,
        "hashrate_current": current_hashrate,
        "hashrate_data_fresh": hashrate_data_fresh,
        "status": status,
    }


def normalize_worker_record(worker: dict[str, Any], fallback_id: str = WORKER_FALLBACK_NAME) -> dict[str, Any]:
    resolved_name = _as_stripped_text(worker.get("name") or worker.get("id") or worker.get("worker"), fallback_id)
    resolved_remote = _as_stripped_text(worker.get("remote_address"), "N/A")
    normalized = build_worker_record(
        name=resolved_name,
        remote_address=resolved_remote,
        difficulty=parse_int(str(worker.get("difficulty", 0)), 0),
        total_hashes=parse_int(str(worker.get("total_hashes", 0)), 0),
        last_share_age_seconds=parse_int(str(worker.get("last_share_age_seconds", 0)), 0),
        shares_found=parse_int(str(worker.get("shares_found", 0)), 0),
        hashrate=float(worker.get("hashrate", 0) or 0),
        hashrate_1h=float(worker.get("hashrate_1h", worker.get("hashrate", 0)) or 0),
        hashrate_current=float(worker.get("hashrate_current", worker.get("hashrate", 0)) or 0),
        hashrate_data_fresh=bool(worker.get("hashrate_data_fresh", True)),
        status=_as_stripped_text(worker.get("status"), "online"),
    )
    normalized["last_seen_ago_seconds"] = parse_int(str(worker.get("last_seen_ago_seconds", 0)), 0)
    normalized["last_seen_ts"] = parse_int(str(worker.get("last_seen_ts", 0)), 0)
    normalized["offline_since_ts"] = parse_int(str(worker.get("offline_since_ts", 0)), 0)
    if "uptime" in worker:
        normalized["uptime"] = worker.get("uptime")
    return normalized


def parse_worker_from_api(raw: str) -> dict[str, Any]:
    parts = [item.strip() for item in raw.split(",")]
    remote_address = parts[0] if len(parts) > 0 else "N/A"
    uptime_seconds = parse_int(parts[1], 0) if len(parts) > 1 else 0
    difficulty = parse_int(parts[2], 0) if len(parts) > 2 else 0
    try:
        hashrate_current = float(parts[3]) if len(parts) > 3 else 0.0
    except ValueError:
        hashrate_current = 0.0
    name = parts[4] if len(parts) > 4 and parts[4] else remote_address
    return build_worker_record(
        name=name,
        remote_address=remote_address,
        difficulty=difficulty,
        last_share_age_seconds=uptime_seconds,
        shares_found=0,
        hashrate=hashrate_current,
        hashrate_1h=hashrate_current,
        hashrate_current=hashrate_current,
        hashrate_data_fresh=True,
        status="online",
    )


def merge_workers_by_name(workers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    for worker in workers:
        candidate = normalize_worker_record(worker)
        key = str(candidate.get("worker_key") or "")

        current = merged.get(key)
        if current is None:
            merged[key] = candidate
            continue

        cand_total = parse_int(str(candidate.get("total_hashes", 0)), 0)
        curr_total = parse_int(str(current.get("total_hashes", 0)), 0)
        cand_rate = float(candidate.get("hashrate", candidate.get("hashrate_current", 0)) or 0)
        curr_rate = float(current.get("hashrate", current.get("hashrate_current", 0)) or 0)

        if cand_total > curr_total or (cand_total == curr_total and cand_rate > curr_rate):
            merged[key] = candidate

    return list(merged.values())


def parse_workers_from_api(workers_payload: Any) -> list[dict[str, Any]]:
    if not isinstance(workers_payload, list):
        return []
    workers: list[dict[str, Any]] = []
    for entry in workers_payload:
        if isinstance(entry, str) and entry.strip():
            workers.append(parse_worker_from_api(entry.strip()))
        elif isinstance(entry, dict):
            workers.append(normalize_worker_record(entry))
    return merge_workers_by_name(workers)


def reconcile_workers(
    current_workers: list[dict[str, Any]],
    worker_state: dict[str, dict[str, Any]],
    now_ts: int,
    recently_offline_seconds: int,
    retention_seconds: int,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    updated_state: dict[str, dict[str, Any]] = dict(worker_state)
    present_ids: set[str] = set()

    for worker in current_workers:
        worker_id = str(worker.get("worker_key") or worker.get("id") or "")
        if not worker_id:
            continue
        present_ids.add(worker_id)
        state_row = dict(updated_state.get(worker_id, {}))

        state_row.update(worker)
        state_row["hashrate_current"] = float(worker.get("hashrate_current", worker.get("hashrate", 0)) or 0)
        state_row["hashrate_data_fresh"] = True
        state_row["last_seen_ts"] = now_ts
        state_row["offline_since_ts"] = 0
        state_row["status"] = "online"
        updated_state[worker_id] = state_row

    display_workers: list[dict[str, Any]] = []
    stale_ids: list[str] = []
    for worker_id, row in updated_state.items():
        merged = dict(row)
        last_seen = parse_int(str(merged.get("last_seen_ts", 0)), 0)
        elapsed = max(0, now_ts - last_seen)

        if worker_id in present_ids:
            merged["status"] = "online"
            merged["last_seen_ago_seconds"] = 0
            display_workers.append(merged)
            updated_state[worker_id] = merged
            continue

        if elapsed <= recently_offline_seconds:
            if parse_int(str(merged.get("offline_since_ts", 0)), 0) <= 0:
                merged["offline_since_ts"] = now_ts
            merged["status"] = "recently_offline"
            merged["last_seen_ago_seconds"] = elapsed
            display_workers.append(merged)
            updated_state[worker_id] = merged
            continue

        if elapsed <= retention_seconds:
            if parse_int(str(merged.get("offline_since_ts", 0)), 0) <= 0:
                merged["offline_since_ts"] = now_ts
            merged["status"] = "offline"
            merged["last_seen_ago_seconds"] = elapsed
            display_workers.append(merged)
            updated_state[worker_id] = merged
            continue

        stale_ids.append(worker_id)

    for stale_id in stale_ids:
        updated_state.pop(stale_id, None)

    status_order = {"online": 0, "recently_offline": 1, "offline": 2}
    display_workers.sort(
        key=lambda item: (
            status_order.get(str(item.get("status", "")), 9),
            parse_int(str(item.get("last_seen_ago_seconds", 0)), 0),
            str(item.get("name", "")),
        )
    )
    return display_workers, updated_state


def normalize_workers_for_render(workers_payload: Any) -> list[dict[str, Any]]:
    if not isinstance(workers_payload, list):
        return []

    normalized_workers: list[dict[str, Any]] = []
    for worker in workers_payload:
        if not isinstance(worker, dict):
            continue
        normalized_workers.append(normalize_worker_record(worker))
    return normalized_workers
