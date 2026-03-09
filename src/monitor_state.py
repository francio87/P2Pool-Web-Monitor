from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


def parse_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_empty_state(schema_version: int) -> dict[str, Any]:
    return {
        "meta": {
            "schema_version": schema_version,
        },
        "history": [],
        "workers_state": {},
    }


def load_state(
    path: Path,
    *,
    schema_version: int,
    normalize_worker_record: Callable[[dict[str, Any], str], dict[str, Any]],
) -> dict[str, Any]:
    if not path.exists():
        return build_empty_state(schema_version)
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            return build_empty_state(schema_version)

        history = loaded.get("history", [])
        workers_state = loaded.get("workers_state", {})
        meta = loaded.get("meta", {})

        if not isinstance(history, list):
            history = []
        if not isinstance(workers_state, dict):
            workers_state = {}
        if not isinstance(meta, dict):
            meta = {}

        normalized_history = [entry for entry in history if isinstance(entry, dict)]
        normalized_workers: dict[str, dict[str, Any]] = {}
        for worker_id, worker in workers_state.items():
            if isinstance(worker_id, str) and isinstance(worker, dict):
                normalized_worker = normalize_worker_record(worker, worker_id.split("|")[0] or worker_id)
                normalized_key = str(normalized_worker.get("worker_key") or worker_id)
                existing = normalized_workers.get(normalized_key)
                if existing is None:
                    normalized_workers[normalized_key] = normalized_worker
                    continue

                existing_last_seen = parse_int(str(existing.get("last_seen_ts", 0)), 0)
                current_last_seen = parse_int(str(normalized_worker.get("last_seen_ts", 0)), 0)
                if current_last_seen >= existing_last_seen:
                    normalized_workers[normalized_key] = normalized_worker

        return {
            "meta": {
                "schema_version": parse_int(str(meta.get("schema_version", schema_version)), schema_version),
            },
            "history": normalized_history,
            "workers_state": normalized_workers,
        }
    except (OSError, json.JSONDecodeError):
        return build_empty_state(schema_version)


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(state, ensure_ascii=True), encoding="utf-8")
    tmp_path.replace(path)
