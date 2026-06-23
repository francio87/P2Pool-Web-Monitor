from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any


DEFAULT_VERSION_CHECK_ENABLED = True
DEFAULT_VERSION_CHECK_INTERVAL_SECONDS = 6 * 60 * 60
DEFAULT_VERSION_CHECK_TIMEOUT_SECONDS = 3
P2POOL_LATEST_RELEASE_URL = "https://api.github.com/repos/SChernykh/p2pool/releases/latest"
P2POOL_TAGS_URL = "https://api.github.com/repos/SChernykh/p2pool/tags?per_page=1"


def resolve_p2pool_version_check_enabled() -> bool:
    raw = os.getenv("P2POOL_VERSION_CHECK")
    if raw is None or not raw.strip():
        return DEFAULT_VERSION_CHECK_ENABLED
    return raw.strip().lower() not in {"0", "false", "no", "off", "disabled"}


def parse_version_number(version: str) -> tuple[int, ...]:
    match = re.search(r"\bv?(\d+(?:\.\d+)*)\b", str(version or ""), flags=re.IGNORECASE)
    if not match:
        return ()
    return tuple(int(part) for part in match.group(1).split("."))


def normalize_version_label(version: str) -> str:
    parsed = parse_version_number(version)
    if not parsed:
        return ""
    return ".".join(str(part) for part in parsed)


def is_newer_version(latest: str, current: str) -> bool:
    latest_parts = parse_version_number(latest)
    current_parts = parse_version_number(current)
    if not latest_parts or not current_parts:
        return False
    width = max(len(latest_parts), len(current_parts))
    latest_padded = latest_parts + (0,) * (width - len(latest_parts))
    current_padded = current_parts + (0,) * (width - len(current_parts))
    return latest_padded > current_padded


def _fetch_json(url: str, timeout: int) -> dict[str, Any] | list[Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "p2pool-web-monitor/version-check",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_latest_p2pool_version(timeout: int = DEFAULT_VERSION_CHECK_TIMEOUT_SECONDS) -> str:
    try:
        release_payload = _fetch_json(P2POOL_LATEST_RELEASE_URL, timeout)
        if isinstance(release_payload, dict):
            version = normalize_version_label(str(release_payload.get("tag_name") or release_payload.get("name") or ""))
            if version:
                return version
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        pass

    tags_payload = _fetch_json(P2POOL_TAGS_URL, timeout)
    if isinstance(tags_payload, list) and tags_payload:
        first = tags_payload[0]
        if isinstance(first, dict):
            return normalize_version_label(str(first.get("name") or ""))
    return ""


def build_disabled_version_check() -> dict[str, Any]:
    return {
        "enabled": False,
        "latest_version": "",
        "update_available": False,
        "last_checked_ts": 0,
        "error": None,
    }


def update_p2pool_version_check(
    data: dict[str, Any],
    cache: dict[str, Any],
    *,
    now_ts: int | None = None,
) -> dict[str, Any]:
    enabled = resolve_p2pool_version_check_enabled()
    p2p = data.setdefault("p2p", {})
    if not enabled:
        p2p["version_check"] = build_disabled_version_check()
        return cache

    timestamp_now = now_ts if now_ts is not None else int(time.time())
    current_version = normalize_version_label(str(p2p.get("p2pool_version", "")))
    last_checked = int(cache.get("last_checked_ts", 0) or 0)
    latest_version = str(cache.get("latest_version", "") or "")
    error = cache.get("error")

    if not latest_version or timestamp_now - last_checked >= DEFAULT_VERSION_CHECK_INTERVAL_SECONDS:
        try:
            latest_version = fetch_latest_p2pool_version()
            error = None if latest_version else "latest_version_not_found"
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        last_checked = timestamp_now
        cache.update({"latest_version": latest_version, "last_checked_ts": last_checked, "error": error})

    update_available = bool(current_version and latest_version and is_newer_version(latest_version, current_version))
    p2p["version_check"] = {
        "enabled": True,
        "latest_version": latest_version,
        "update_available": update_available,
        "last_checked_ts": last_checked,
        "error": error,
    }

    if update_available:
        reliability = data.setdefault("reliability", {})
        reasons = reliability.setdefault("reasons", [])
        if isinstance(reasons, list) and "p2pool_update_available" not in reasons:
            reasons.append("p2pool_update_available")
            reasons.sort()

    return cache
