#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def validate_json_file(path: Path, *, max_age_seconds: int | None = None) -> int:
    if not path.exists():
        return fail(f"missing file: {path}")
    if not path.is_file() or path.stat().st_size <= 0:
        return fail(f"empty or invalid file: {path}")

    if max_age_seconds is not None:
        age_seconds = int(time.time() - path.stat().st_mtime)
        if age_seconds > max_age_seconds:
            return fail(f"stale file: {path} age={age_seconds}s max={max_age_seconds}s")

    try:
        json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"invalid json: {path}: {exc}")

    return 0


def validate_http(url: str, *, timeout_seconds: int) -> int:
    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            if response.status < 200 or response.status >= 400:
                return fail(f"http check failed: {url} status={response.status}")
            response.read(1)
    except Exception as exc:  # noqa: BLE001
        return fail(f"http check failed: {url}: {exc}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Container healthcheck for p2pool-web-monitor")
    parser.add_argument("--output-dir", default="/output")
    parser.add_argument("--max-age", type=int, default=120)
    parser.add_argument("--http-url", default="http://127.0.0.1:8080/index.html")
    parser.add_argument("--http-timeout", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)

    checks = [
        validate_json_file(output_dir / "data.json", max_age_seconds=args.max_age),
        validate_json_file(output_dir / "history.json"),
        validate_http(args.http_url, timeout_seconds=args.http_timeout),
    ]
    return 0 if all(code == 0 for code in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
