#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time
from pathlib import Path

from monitor_common import (
    DEFAULT_REFRESH_SECONDS,
    DEFAULT_HISTORY_BUCKET_SECONDS,
    DEFAULT_HISTORY_RETENTION_SECONDS,
    STATE_SCHEMA_VERSION,
    deep_copy_default_results,
    format_duration_seconds,
    format_hashrate,
    format_number,
    format_time_ago,
    format_unix_datetime,
    format_xmr,
    get_observer_base_url,
    load_dotenv,
    normalize_sidechain_mode,
    parse_int,
    parse_uptime_to_seconds,
    resolve_worker_recently_offline_seconds,
    resolve_worker_retention_seconds,
    truncate_wallet,
    to_hashrate,
)
from monitor_history import update_history
from monitor_parsing import (
    compute_reliability,
    fetch_p2pool_data_from_disk,
    parse_log_file,
    parse_status_blocks,
    parse_workers_from_log,
)
from monitor_paths import (
    resolve_data_output_path,
    resolve_input_dir,
    resolve_output_path,
    validate_input_dir,
)
from monitor_render import (
    build_render_data,
    print_verbose_summary,
    render_json,
)
from monitor_state import load_state, save_state
from monitor_workers import (
    normalize_worker_record,
    parse_worker_from_api,
    parse_workers_from_api,
    reconcile_workers,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="p2pool_web_monitor.py",
        usage="%(prog)s [-h] [--once] [-p P2POOL_DIR] [--data-api-dir DATA_API_DIR] [-o OUTPUT] [-v] [-d]",
        description="P2Pool Web Monitor - generate live dashboard data from local P2Pool logs and APIs.",
        epilog=(
            "Examples:\n"
            "  python3 src/p2pool_web_monitor.py -p /p2pool-data --data-api-dir /p2pool-data --once\n"
            "  python3 src/p2pool_web_monitor.py -o web/index.html --once\n"
            "  python3 src/p2pool_web_monitor.py -o web --once\n"
            "  python3 src/p2pool_web_monitor.py --verbose\n"
            "  python3 src/p2pool_web_monitor.py -p /var/lib/p2pool\n"
            "  python3 src/p2pool_web_monitor.py -p /var/lib/p2pool --data-api-dir /var/lib/p2pool/data-api"
        ),
        formatter_class=lambda prog: argparse.RawTextHelpFormatter(
            prog,
            max_help_position=32,
            width=100,
        ),
    )
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("-p", "--p2pool-dir", help="Path to local P2Pool data directory")
    parser.add_argument("-o", "--output", help="Output file path (.html) or output directory")
    parser.add_argument(
        "--data-api-dir",
        help="Explicit P2Pool data-api directory (contains local/, pool/, network/)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-d", "--debug", action="store_true", help="Debug output")
    return parser.parse_args()


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    load_dotenv(script_dir.parent / ".env")
    args = parse_args()

    history_max_points = max(1, DEFAULT_HISTORY_RETENTION_SECONDS // max(60, DEFAULT_HISTORY_BUCKET_SECONDS))
    input_dir = resolve_input_dir(args.p2pool_dir, args.data_api_dir)
    output_path = resolve_output_path(args.output, script_dir)
    history_path = output_path.parent / "history.json"
    data_output_path = resolve_data_output_path(output_path)

    state = load_state(
        history_path,
        schema_version=STATE_SCHEMA_VERSION,
        normalize_worker_record=normalize_worker_record,
    )
    history = state.get("history", []) if isinstance(state.get("history"), list) else []
    worker_state = state.get("workers_state", {}) if isinstance(state.get("workers_state"), dict) else {}

    print(f"Starting P2Pool Web Monitor (input: {input_dir}, output: {output_path})")
    while True:
        try:
            data, worker_state = fetch_p2pool_data_from_disk(
                str(input_dir),
                data_api_dir=args.data_api_dir,
                worker_state=worker_state,
            )
            history = update_history(
                history,
                data,
                max_points=history_max_points,
                bucket_seconds=DEFAULT_HISTORY_BUCKET_SECONDS,
            )
            save_state(
                history_path,
                {
                    "meta": {"schema_version": STATE_SCHEMA_VERSION},
                    "history": history,
                    "workers_state": worker_state,
                },
            )
            render_json(data_output_path, build_render_data(data, history))

            print(f"[+] Stats data generated ({data_output_path.name})")
            if args.verbose or args.debug:
                print_verbose_summary(data)
        except Exception as exc:  # noqa: BLE001
            print(f"[X] Failed to generate stats data: {exc}")
            if args.debug:
                raise

        if args.once:
            break
        time.sleep(DEFAULT_REFRESH_SECONDS)


if __name__ == "__main__":
    main()
