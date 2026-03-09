from __future__ import annotations

import json
import os
from pathlib import Path

from monitor_common import REQUIRED_LOG_CANDIDATES


def load_json_file(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def count_nonempty_lines(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except OSError:
        return 0


def get_mtime_unix(path: Path) -> int:
    try:
        return int(path.stat().st_mtime)
    except OSError:
        return 0


def safe_relative(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def resolve_data_api_dir(base_dir: Path, explicit_data_api_dir: str | None = None) -> Path | None:
    candidates: list[Path] = []
    if explicit_data_api_dir:
        candidates.append(Path(explicit_data_api_dir))
    env_data_api = os.getenv("DATA_API_DIR")
    if env_data_api:
        candidates.append(Path(env_data_api))
    candidates.append(base_dir / "data-api")
    candidates.append(base_dir)

    for candidate in candidates:
        if not candidate.exists() or not candidate.is_dir():
            continue
        if (candidate / "local").exists() or (candidate / "pool").exists() or (candidate / "network").exists():
            return candidate
    return None


def resolve_required_log_path(path: Path) -> Path | None:
    for rel in REQUIRED_LOG_CANDIDATES:
        candidate = path / rel
        if candidate.exists():
            return candidate
    return None


def validate_input_dir(path: Path, data_api_dir: str | None = None) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if not path.exists() or not path.is_dir():
        return False, [f"Directory not found: {path}"]

    log_ok = resolve_required_log_path(path) is not None
    api_ok = resolve_data_api_dir(path, data_api_dir) is not None
    if not log_ok and not api_ok:
        joined_logs = ", ".join(REQUIRED_LOG_CANDIDATES)
        missing.append(
            f"Missing both log and data-api inputs in {path} (logs checked: {joined_logs}; expected data-api dirs: data-api/ or root with local/, pool/, network/)."
        )
    return len(missing) == 0, missing


def resolve_input_dir(cli_dir: str | None, data_api_dir: str | None = None) -> Path:
    candidates: list[Path] = []
    if cli_dir:
        candidates.append(Path(cli_dir))
    env_dir = os.getenv("P2POOL_DIR")
    if env_dir:
        candidates.append(Path(env_dir))
    candidates.append(Path.cwd())

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve()) if candidate.exists() else str(candidate)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)

    for candidate in deduped:
        valid, _ = validate_input_dir(candidate, data_api_dir)
        if valid:
            return candidate

    print("[X] Missing required local P2Pool inputs.")
    print("Checked directories:")
    for candidate in deduped:
        print(f"  - {candidate}")
    print("Accepted log file paths (one may exist):")
    for req in REQUIRED_LOG_CANDIDATES:
        print(f"  - {req}")
    print("Accepted data-api layouts (one may exist):")
    print("  - data-api/local + data-api/pool + data-api/network")
    print("  - local + pool + network")
    print("Hint: use -h or --help to view all options.")
    print("Example: python3 src/p2pool_web_monitor.py -p /path/to/p2pool --once")
    raise SystemExit(1)


def resolve_output_path(cli_output: str | None, base_dir: Path) -> Path:
    configured = cli_output or os.getenv("OUTPUT") or str(base_dir.parent / "web" / "index.html")
    candidate = Path(configured)
    if candidate.suffix.lower() == ".html":
        return candidate
    return candidate / "index.html"


def resolve_data_output_path(primary_output: Path) -> Path:
    return primary_output.with_name("data.json")
