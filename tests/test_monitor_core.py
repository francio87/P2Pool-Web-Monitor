from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from monitor_common import (  # noqa: E402
    SIDECHAIN_OBSERVER_BASE_URLS,
    format_duration_seconds,
    get_observer_base_url,
    normalize_sidechain_mode,
    parse_uptime_to_seconds,
)
from monitor_history import build_history_point, update_history  # noqa: E402
from monitor_version import (  # noqa: E402
    is_newer_version,
    normalize_version_label,
    parse_version_number,
)
from monitor_workers import (  # noqa: E402
    build_worker_record,
    parse_workers_from_api,
    reconcile_workers,
)


class MonitorCoreTests(unittest.TestCase):
    def test_sidechain_mode_normalization_and_observer_urls(self) -> None:
        self.assertEqual(normalize_sidechain_mode(None), "unknown")
        self.assertEqual(normalize_sidechain_mode("  MiNi  "), "mini")
        self.assertEqual(normalize_sidechain_mode("nano relay"), "nano")
        self.assertEqual(normalize_sidechain_mode("p2pool"), "main")
        self.assertEqual(get_observer_base_url("mini"), SIDECHAIN_OBSERVER_BASE_URLS["mini"])
        self.assertEqual(get_observer_base_url("nonsense"), SIDECHAIN_OBSERVER_BASE_URLS["main"])

    def test_uptime_parsing_and_duration_formatting(self) -> None:
        seconds = parse_uptime_to_seconds("1d 2h 3m 4s")
        self.assertEqual(seconds, 93_784)
        self.assertEqual(format_duration_seconds(seconds), "1d 2h 3m 4s")

    def test_version_helpers(self) -> None:
        self.assertEqual(parse_version_number("release v2.9.0-rc1"), (2, 9, 0))
        self.assertEqual(normalize_version_label("P2Pool v2.9.0"), "2.9.0")
        self.assertTrue(is_newer_version("2.10.0", "2.9.9"))
        self.assertFalse(is_newer_version("2.9.0", "2.9.0"))
        self.assertFalse(is_newer_version("invalid", "2.9.0"))

    def test_update_history_fills_gaps_and_trims_to_max_points(self) -> None:
        history = [
            build_history_point(
                0,
                samples=1,
                h15_sum=10.0,
                h1_sum=20.0,
                h15_avg=10.0,
                h1_avg=20.0,
                shares_last=1,
                shares_delta=1,
            )
        ]
        data = {"stratum": {"hashrate_15m": 12.5, "hashrate_1h": 25.0, "shares_found": 4}}

        updated = update_history(history, data, max_points=3, bucket_seconds=60, now_ts=180)

        self.assertEqual([point["bucket_ts"] for point in updated], [60, 120, 180])
        self.assertEqual(updated[0]["samples"], 0)
        self.assertEqual(updated[1]["samples"], 0)
        self.assertEqual(updated[2]["samples"], 1)
        self.assertEqual(updated[0]["shares_last"], 1)
        self.assertEqual(updated[1]["shares_last"], 1)
        self.assertEqual(updated[2]["shares_last"], 4)
        self.assertEqual(updated[2]["shares_delta"], 0)

    def test_parse_workers_from_api_merges_duplicate_workers(self) -> None:
        workers = parse_workers_from_api(
            [
                {"name": "alpha", "remote_address": "1.2.3.4:3333", "total_hashes": 10, "hashrate": 1.0},
                {"name": " alpha ", "remote_address": "1.2.3.4:3333", "total_hashes": 20, "hashrate": 0.5},
                "5.6.7.8:3333,60,100,42.5,beta",
            ]
        )

        self.assertEqual(len(workers), 2)
        workers_by_name = {worker["name"]: worker for worker in workers}
        self.assertEqual(workers_by_name["alpha"]["total_hashes"], 20)
        self.assertEqual(workers_by_name["alpha"]["hashrate"], 0.5)
        self.assertEqual(workers_by_name["beta"]["remote_address"], "5.6.7.8:3333")
        self.assertEqual(workers_by_name["beta"]["hashrate_current"], 42.5)

    def test_reconcile_workers_tracks_status_transitions_and_drops_stale_workers(self) -> None:
        current_worker = build_worker_record(
            name="alpha",
            remote_address="1.2.3.4:3333",
            hashrate=5.0,
            hashrate_1h=5.0,
            hashrate_current=5.0,
        )
        current_workers = [current_worker]
        worker_state = {
            "alpha": {
                **build_worker_record(name="alpha", remote_address="1.2.3.4:3333", hashrate=4.0),
                "last_seen_ts": 1_000,
                "offline_since_ts": 0,
                "status": "online",
            },
            "beta": {
                **build_worker_record(name="beta", remote_address="5.6.7.8:3333", hashrate=2.0),
                "last_seen_ts": 1_200,
                "offline_since_ts": 0,
                "status": "online",
            },
            "gamma": {
                **build_worker_record(name="gamma", remote_address="9.9.9.9:3333", hashrate=1.0),
                "last_seen_ts": 100,
                "offline_since_ts": 0,
                "status": "online",
            },
        }

        display_workers, updated_state = reconcile_workers(
            current_workers,
            worker_state,
            now_ts=1_300,
            recently_offline_seconds=200,
            retention_seconds=1_000,
        )

        self.assertEqual({worker["name"] for worker in display_workers}, {"alpha", "beta"})
        display_by_name = {worker["name"]: worker for worker in display_workers}
        self.assertEqual(display_by_name["alpha"]["status"], "online")
        self.assertEqual(display_by_name["beta"]["status"], "recently_offline")
        self.assertEqual(display_by_name["beta"]["offline_since_ts"], 1_300)
        self.assertNotIn("gamma", updated_state)
        self.assertEqual(set(updated_state), {"alpha", "beta"})
        self.assertEqual(updated_state["alpha"]["status"], "online")
        self.assertEqual(updated_state["beta"]["status"], "recently_offline")


if __name__ == "__main__":
    unittest.main()
