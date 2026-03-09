from __future__ import annotations

import time
from datetime import datetime
from typing import Any


def parse_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_history_point(
    bucket_ts: int,
    *,
    samples: int,
    h15_sum: float,
    h1_sum: float,
    h15_avg: float,
    h1_avg: float,
    shares_last: int,
    shares_delta: int,
) -> dict[str, Any]:
    return {
        "bucket_ts": bucket_ts,
        "label": datetime.fromtimestamp(bucket_ts).strftime("%H:%M"),
        "samples": samples,
        "h15_sum": h15_sum,
        "h1_sum": h1_sum,
        "h15_avg": h15_avg,
        "h1_avg": h1_avg,
        "shares_last": shares_last,
        "shares_delta": shares_delta,
    }


def build_empty_history_point(bucket_ts: int, shares_last: int) -> dict[str, Any]:
    return build_history_point(
        bucket_ts,
        samples=0,
        h15_sum=0.0,
        h1_sum=0.0,
        h15_avg=0.0,
        h1_avg=0.0,
        shares_last=shares_last,
        shares_delta=0,
    )


def normalize_history_points(history: list[dict[str, Any]], bucket_seconds: int) -> list[dict[str, Any]]:
    if not history:
        return history

    normalized: list[dict[str, Any]] = []
    for point in history:
        if not isinstance(point, dict):
            continue
        if not normalized:
            normalized.append(point)
            continue

        prev_ts = int(normalized[-1].get("bucket_ts", 0) or 0)
        current_ts = int(point.get("bucket_ts", 0) or 0)
        if current_ts <= prev_ts:
            continue

        next_bucket_ts = prev_ts + bucket_seconds
        while next_bucket_ts < current_ts:
            normalized.append(build_empty_history_point(next_bucket_ts, int(normalized[-1].get("shares_last", 0) or 0)))
            next_bucket_ts += bucket_seconds

        normalized.append(point)
    return normalized


def fill_history_gaps(history: list[dict[str, Any]], bucket_ts: int, bucket_seconds: int) -> bool:
    had_gap = False
    if not history:
        return had_gap

    next_bucket_ts = int(history[-1].get("bucket_ts", 0) or 0) + bucket_seconds
    while next_bucket_ts < bucket_ts:
        had_gap = True
        history.append(build_empty_history_point(next_bucket_ts, int(history[-1].get("shares_last", 0) or 0)))
        next_bucket_ts += bucket_seconds
    return had_gap


def update_existing_history_point(point: dict[str, Any], h15: float, h1: float, shares_now: int, label: str) -> None:
    samples = parse_int(str(point.get("samples", 1)), 1) + 1
    h15_sum = float(point.get("h15_sum", point.get("h15_avg", 0)) or 0) + h15
    h1_sum = float(point.get("h1_sum", point.get("h1_avg", 0)) or 0) + h1
    prev_last = int(point.get("shares_last", shares_now) or shares_now)
    delta_increment = shares_now - prev_last if shares_now >= prev_last else shares_now

    point["samples"] = samples
    point["h15_sum"] = h15_sum
    point["h1_sum"] = h1_sum
    point["h15_avg"] = h15_sum / samples
    point["h1_avg"] = h1_sum / samples
    point["shares_last"] = shares_now
    point["shares_delta"] = int(point.get("shares_delta", 0) or 0) + delta_increment
    point["label"] = label


def append_history_point(
    history: list[dict[str, Any]],
    *,
    bucket_ts: int,
    h15: float,
    h1: float,
    shares_now: int,
    had_gap: bool,
) -> None:
    prev_last = int(history[-1].get("shares_last", 0) or 0) if history else shares_now
    shares_delta = 0 if had_gap else (shares_now - prev_last if shares_now >= prev_last else shares_now)
    history.append(
        build_history_point(
            bucket_ts,
            samples=1,
            h15_sum=h15,
            h1_sum=h1,
            h15_avg=h15,
            h1_avg=h1,
            shares_last=shares_now,
            shares_delta=shares_delta if history else 0,
        )
    )


def update_history(
    history: list[dict[str, Any]],
    data: dict[str, Any],
    max_points: int,
    bucket_seconds: int,
    now_ts: int | None = None,
) -> list[dict[str, Any]]:
    ts = now_ts if now_ts is not None else int(time.time())
    bucket = max(60, bucket_seconds)
    bucket_ts = ts - (ts % bucket)
    label = datetime.fromtimestamp(bucket_ts).strftime("%H:%M")

    history = normalize_history_points(history, bucket)

    stratum = data.get("stratum", {})
    if not isinstance(stratum, dict):
        stratum = {}

    h15 = float(stratum.get("hashrate_15m", 0) or 0)
    h1 = float(stratum.get("hashrate_1h", 0) or 0)
    shares_now = int(stratum.get("shares_found", 0) or 0)

    had_gap = fill_history_gaps(history, bucket_ts, bucket)

    if history and history[-1].get("bucket_ts") == bucket_ts:
        update_existing_history_point(history[-1], h15, h1, shares_now, label)
    else:
        append_history_point(
            history,
            bucket_ts=bucket_ts,
            h15=h15,
            h1=h1,
            shares_now=shares_now,
            had_gap=had_gap,
        )

    if len(history) > max_points:
        history = history[-max_points:]
    return history
