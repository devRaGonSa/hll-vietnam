from __future__ import annotations

import json
import os
import sys
import unittest
from contextlib import contextmanager
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class _ExampleEnum(Enum):
    VALUE = "value"


@contextmanager
def _noop_writer_lock(*args, **kwargs):
    yield {"lock": "test"}


class HistoricalPipelineRegressionTests(unittest.TestCase):
    def test_known_degraded_s3_is_operable_by_fallback(self) -> None:
        from app import data_sources
        from app.config import get_historical_known_rcon_degraded_targets

        status = {
            "target_key": "comunidad-hispana-03",
            "external_server_id": "comunidad-hispana-03",
            "display_name": "Comunidad Hispana #03",
            "last_run_status": "failed",
            "last_error": "Login failed with RCON status 401: Missing authentication credentials.",
            "last_error_at": "2026-04-16T00:00:00Z",
            "last_successful_capture_at": None,
            "last_sample_at": None,
        }

        with patch.dict(os.environ, {}, clear=False), patch.object(
            data_sources,
            "get_historical_data_source_kind",
            return_value=data_sources.SOURCE_KIND_RCON,
        ), patch.object(
            data_sources,
            "list_rcon_historical_target_statuses",
            return_value=[status],
        ):
            self.assertIn(
                "comunidad-hispana-03",
                get_historical_known_rcon_degraded_targets(),
            )
            runtime_policy = data_sources.describe_historical_runtime_policy()
            health = data_sources.describe_historical_rcon_target_health(
                server_key="comunidad-hispana-03"
            )

        self.assertEqual(runtime_policy["primary_source"], data_sources.SOURCE_KIND_RCON)
        self.assertEqual(
            runtime_policy["fallback_source"],
            data_sources.SOURCE_KIND_PUBLIC_SCOREBOARD,
        )
        self.assertIn(
            "comunidad-hispana-03",
            runtime_policy["operational_degraded_targets"],
        )
        self.assertTrue(health["fallback_eligible"])
        self.assertEqual(health["reason"], "rcon-target-known-operational-degraded")
        self.assertEqual(
            health["fallback_reason"],
            "known-rcon-degraded-target-operable-via-public-scoreboard",
        )
        self.assertTrue(health["target"]["configured_as_known_degraded"])

    def test_source_policy_keeps_rcon_primary_and_public_scoreboard_fallback(self) -> None:
        from app import data_sources

        with patch.object(
            data_sources,
            "get_historical_data_source_kind",
            return_value=data_sources.SOURCE_KIND_RCON,
        ):
            policy = data_sources.build_historical_runtime_source_policy(
                operation="historical-ingestion",
                rcon_status="degraded",
                selected_source=data_sources.SOURCE_KIND_PUBLIC_SCOREBOARD,
                fallback_reason="known-rcon-degraded-target-operable-via-public-scoreboard",
                rcon_message="auth/login failed",
            )

        self.assertEqual(policy["primary_source"], data_sources.SOURCE_KIND_RCON)
        self.assertEqual(
            policy["selected_source"],
            data_sources.SOURCE_KIND_PUBLIC_SCOREBOARD,
        )
        self.assertTrue(policy["fallback_used"])
        self.assertEqual(
            policy["fallback_reason"],
            "known-rcon-degraded-target-operable-via-public-scoreboard",
        )
        self.assertEqual(policy["source_attempts"][0]["source"], data_sources.SOURCE_KIND_RCON)
        self.assertEqual(policy["source_attempts"][0]["status"], "degraded")
        self.assertEqual(
            policy["source_attempts"][1]["source"],
            data_sources.SOURCE_KIND_PUBLIC_SCOREBOARD,
        )
        self.assertEqual(policy["source_attempts"][1]["role"], "fallback")

    def test_recent_sweep_forces_page_one_and_skips_direct_snapshot_rebuild(self) -> None:
        from app import historical_ingestion

        captured: dict[str, object] = {}

        def fake_run_ingestion(**kwargs):
            captured.update(kwargs)
            return {"status": "ok", "totals": {}}

        with patch.object(
            historical_ingestion,
            "backend_writer_lock",
            _noop_writer_lock,
        ), patch.object(
            historical_ingestion,
            "_run_ingestion",
            side_effect=fake_run_ingestion,
        ):
            result = historical_ingestion.run_recent_repair_sweep(
                server_slug="comunidad-hispana-03",
                pages=3,
                page_size=10,
                detail_workers=2,
            )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(captured["mode"], "recent-sweep")
        self.assertEqual(captured["start_page"], 1)
        self.assertEqual(captured["max_pages"], 3)
        self.assertEqual(captured["page_size"], 10)
        self.assertFalse(captured["rebuild_snapshots"])

    def test_refresh_server_page_failure_is_isolated_and_later_servers_continue(self) -> None:
        from app import historical_ingestion
        from app.data_sources import SOURCE_KIND_PUBLIC_SCOREBOARD, SOURCE_KIND_RCON

        servers = [
            {
                "slug": "broken-server",
                "scoreboard_base_url": "https://broken.example",
                "server_number": 1,
            },
            {
                "slug": "healthy-server",
                "scoreboard_base_url": "https://healthy.example",
                "server_number": 2,
            },
        ]

        class FakeDataSource:
            source_kind = SOURCE_KIND_PUBLIC_SCOREBOARD

            def fetch_public_info(self, *, base_url):
                return {"name": base_url}

            def fetch_match_page(self, *, base_url, page, limit):
                if "broken" in base_url:
                    raise RuntimeError("provider page failed")
                return {
                    "total": 1,
                    "maps": [
                        {
                            "id": "match-1",
                            "end": "2026-04-16T10:00:00Z",
                        }
                    ],
                }

            def fetch_match_details(self, *, base_url, match_ids, max_workers):
                return [{"id": match_id, "player_stats": []} for match_id in match_ids]

        with patch.object(historical_ingestion, "_select_servers", return_value=servers), patch.object(
            historical_ingestion,
            "initialize_historical_storage",
            return_value=None,
        ), patch.object(
            historical_ingestion,
            "resolve_historical_ingestion_data_source",
            return_value=(
                FakeDataSource(),
                {
                    "primary_source": SOURCE_KIND_RCON,
                    "selected_source": SOURCE_KIND_PUBLIC_SCOREBOARD,
                    "fallback_used": True,
                },
            ),
        ), patch.object(
            historical_ingestion,
            "_attempt_primary_rcon_writer",
            return_value={
                "status": "empty",
                "selected_source": SOURCE_KIND_PUBLIC_SCOREBOARD,
                "fallback_reason": "test-fallback",
            },
        ), patch.object(
            historical_ingestion,
            "start_ingestion_run",
            side_effect=[101, 102],
        ), patch.object(
            historical_ingestion,
            "mark_backfill_progress_started",
            return_value=None,
        ), patch.object(
            historical_ingestion,
            "finalize_ingestion_run",
            return_value=None,
        ), patch.object(
            historical_ingestion,
            "finalize_backfill_progress",
            return_value=None,
        ), patch.object(
            historical_ingestion,
            "mark_backfill_progress_page_completed",
            return_value=None,
        ), patch.object(
            historical_ingestion,
            "get_refresh_cutoff_for_server",
            return_value=None,
        ), patch.object(
            historical_ingestion,
            "upsert_historical_match",
            return_value={
                "matches_inserted": 1,
                "matches_updated": 0,
                "player_rows_inserted": 0,
                "player_rows_updated": 0,
            },
        ), patch.object(
            historical_ingestion,
            "list_historical_coverage_report",
            return_value=[],
        ):
            result = historical_ingestion._run_ingestion(
                mode="recent-sweep",
                server_slug=None,
                max_pages=1,
                page_size=10,
                start_page=1,
                detail_workers=1,
                overlap_hours=None,
                incremental=False,
                rebuild_snapshots=False,
                progress_callback=None,
            )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["servers"][0]["status"], "failed")
        self.assertEqual(result["servers"][0]["server_slug"], "broken-server")
        self.assertEqual(result["servers"][1]["status"], "success")
        self.assertEqual(result["servers"][1]["server_slug"], "healthy-server")
        self.assertEqual(result["totals"]["matches_inserted"], 1)

    def test_detail_failure_is_isolated_and_marks_existing_match_for_retry(self) -> None:
        from app import historical_ingestion

        class FakeDetailDataSource:
            def fetch_match_details(self, *, base_url, match_ids, max_workers):
                if len(match_ids) > 1:
                    raise RuntimeError("batch failed")
                if match_ids[0] == "bad-match":
                    raise RuntimeError("detail failed")
                return [{"id": match_ids[0], "player_stats": []}]

        with patch.object(
            historical_ingestion,
            "mark_historical_match_detail_repair_failed",
        ) as mark_failed:
            payloads, failure_delta = historical_ingestion._fetch_match_details_resilient(
                data_source=FakeDetailDataSource(),
                server={
                    "slug": "comunidad-hispana-03",
                    "scoreboard_base_url": "https://scoreboard.example",
                },
                match_ids=["good-match", "bad-match"],
                max_workers=4,
                mode="recent-sweep",
                page_number=1,
                progress_callback=None,
            )

        self.assertEqual(payloads, [{"id": "good-match", "player_stats": []}])
        self.assertEqual(failure_delta["matches_inserted"], 0)
        mark_failed.assert_called_once()
        self.assertEqual(mark_failed.call_args.kwargs["server_slug"], "comunidad-hispana-03")
        self.assertEqual(mark_failed.call_args.kwargs["external_match_id"], "bad-match")
        self.assertIn("detail failed", mark_failed.call_args.kwargs["error_message"])

    def test_new_match_detail_failure_persists_minimal_summary_for_retry(self) -> None:
        from app import historical_ingestion

        class FakeDetailDataSource:
            def fetch_match_details(self, *, base_url, match_ids, max_workers):
                if len(match_ids) > 1:
                    raise RuntimeError("batch failed")
                raise RuntimeError("detail failed")

        summary = {
            "id": "new-match",
            "start": "2026-04-16T10:00:00Z",
            "end": "2026-04-16T11:00:00Z",
            "map": {"name": "utahbeach_warfare"},
        }
        with patch.object(
            historical_ingestion,
            "persist_minimal_historical_match_detail_failure",
            return_value={
                "matches_inserted": 1,
                "matches_updated": 0,
                "player_rows_inserted": 0,
                "player_rows_updated": 0,
            },
        ) as persist_minimal, patch.object(
            historical_ingestion,
            "mark_historical_match_detail_repair_failed",
        ) as mark_failed:
            payloads, failure_delta = historical_ingestion._fetch_match_details_resilient(
                data_source=FakeDetailDataSource(),
                server={
                    "slug": "comunidad-hispana-03",
                    "scoreboard_base_url": "https://scoreboard.example",
                },
                match_ids=["new-match"],
                match_summaries_by_id={"new-match": summary},
                max_workers=4,
                mode="recent-sweep",
                page_number=1,
                progress_callback=None,
            )

        self.assertEqual(payloads, [])
        self.assertEqual(failure_delta["matches_inserted"], 1)
        persist_minimal.assert_called_once()
        self.assertEqual(
            persist_minimal.call_args.kwargs["server_slug"],
            "comunidad-hispana-03",
        )
        self.assertEqual(persist_minimal.call_args.kwargs["match_summary"], summary)
        self.assertIn("detail failed", persist_minimal.call_args.kwargs["error_message"])
        mark_failed.assert_not_called()

    def test_cli_json_default_serializes_datetime_date_enum_and_unknown_objects(self) -> None:
        from app.historical_ingestion import _json_default

        payload = {
            "datetime": datetime(2026, 4, 16, 12, 0, tzinfo=timezone.utc),
            "date": date(2026, 4, 16),
            "enum": _ExampleEnum.VALUE,
            "unknown": object(),
        }

        encoded = json.dumps(payload, default=_json_default)

        self.assertIn("2026-04-16T12:00:00Z", encoded)
        self.assertIn("2026-04-16", encoded)
        self.assertIn("value", encoded)

    def test_runner_selective_postprocess_policy_uses_ingestion_signals(self) -> None:
        from app import historical_runner

        no_change = historical_runner._build_heavy_postprocess_policy(
            refresh_result={"totals": {}},
            recent_sweep_result={"totals": {}},
            rcon_capture_result={"status": "ok", "totals": {"samples_inserted": 0}},
            run_number=1,
        )
        inserted_match = historical_runner._build_heavy_postprocess_policy(
            refresh_result={"totals": {"matches_inserted": 1}},
            recent_sweep_result={"totals": {}},
            rcon_capture_result={"status": "ok", "totals": {"samples_inserted": 0}},
            run_number=1,
        )

        self.assertFalse(no_change["due"])
        self.assertEqual(no_change["reason"], "selective-heavy-postprocess-not-due")
        self.assertTrue(inserted_match["due"])
        self.assertEqual(inserted_match["reason"], "new-matches-inserted")

    def test_elo_mmr_match_results_persist_uses_conflict_update(self) -> None:
        from app import elo_mmr_storage

        class FakeConnection:
            def __init__(self) -> None:
                self.executemany_calls: list[tuple[str, object]] = []

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, exc_tb):
                return None

            def executemany(self, query, params):
                self.executemany_calls.append((query, params))

        fake_connection = FakeConnection()

        with patch.object(
            elo_mmr_storage,
            "initialize_elo_mmr_storage",
            return_value=Path("test-db"),
        ), patch.object(
            elo_mmr_storage,
            "_connect_writer",
            return_value=fake_connection,
        ):
            elo_mmr_storage.persist_elo_mmr_match_results(
                match_results=[_build_minimal_elo_match_result()],
            )
            elo_mmr_storage.persist_elo_mmr_match_results(
                match_results=[_build_minimal_elo_match_result(player_name="Updated")],
            )

        self.assertEqual(len(fake_connection.executemany_calls), 2)
        sql = fake_connection.executemany_calls[0][0]
        self.assertIn(
            "ON CONFLICT(scope_key, external_match_id, stable_player_key) DO UPDATE SET",
            sql,
        )
        self.assertIn("updated_at = CURRENT_TIMESTAMP::text", sql)

    def test_material_update_detection_ignores_rereads_and_detects_changes(self) -> None:
        from app import historical_storage

        row = {
            "started_at": "2026-04-16T10:00:00Z",
            "ended_at": "2026-04-16T11:00:00Z",
            "axis_score": 2,
            "allied_score": 3,
            "map_name": "utahbeach_warfare",
        }
        same_values = {
            "started_at": "2026-04-16 10:00:00+00:00",
            "ended_at": "2026-04-16 11:00:00+00:00",
            "axis_score": 2,
            "allied_score": 3,
            "map_name": "utahbeach_warfare",
        }
        changed_values = {**same_values, "axis_score": 5}

        self.assertFalse(historical_storage._row_values_changed(row, same_values))
        self.assertTrue(historical_storage._row_values_changed(row, changed_values))


def _build_minimal_elo_match_result(*, player_name: str = "Player") -> dict[str, object]:
    return {
        "scope_key": "comunidad-hispana-03",
        "month_key": "2026-04",
        "canonical_match_key": "match-1",
        "external_match_id": "1561564",
        "stable_player_key": "player-1",
        "player_name": player_name,
        "steam_id": None,
        "server_slug": "comunidad-hispana-03",
        "server_name": "Comunidad Hispana #03",
        "match_ended_at": "2026-04-16T12:09:34Z",
        "fact_schema_version": "test",
        "source_input_version": "test",
        "model_version": "test",
        "formula_version": "test",
        "contract_version": "test",
        "match_valid": True,
        "quality_factor": 1.0,
        "quality_bucket": "high",
        "role_bucket": "infantry",
        "role_bucket_mode": "exact",
        "outcome_score": 0.0,
        "combat_index": 0.0,
        "objective_index": 0.0,
        "objective_index_mode": "exact",
        "utility_index": 0.0,
        "utility_index_mode": "exact",
        "leadership_index": 0.0,
        "leadership_index_mode": "exact",
        "discipline_index": 0.0,
        "discipline_index_mode": "exact",
        "impact_score": 0.0,
        "delta_mmr": 0.0,
        "mmr_before": 1000.0,
        "mmr_after": 1000.0,
        "match_score": 0.0,
        "penalty_points": 0.0,
        "time_seconds": 3600,
        "participation_ratio": 1.0,
        "strength_of_schedule_match": 0.0,
        "team_outcome": "draw",
        "own_team_average_mmr": 1000.0,
        "enemy_team_average_mmr": 1000.0,
        "expected_result": 0.5,
        "actual_result": 0.5,
        "won_score": 0.0,
        "margin_boost": 0.0,
        "outcome_adjusted": 0.0,
        "match_impact": 0.0,
        "combat_contribution": 0.0,
        "objective_contribution": 0.0,
        "utility_contribution": 0.0,
        "survival_discipline_contribution": 0.0,
        "exact_component_contribution": 0.0,
        "proxy_component_contribution": 0.0,
        "normalization_bucket_key": "test",
        "normalization_fallback_reason": None,
        "elo_core_delta": 0.0,
        "performance_modifier_delta": 0.0,
        "proxy_modifier_delta": 0.0,
        "canonical_fact_capability_status": "available",
        "identity_capability_status": "available",
        "match_duration_seconds": 3600,
        "duration_source_status": "exact",
        "duration_bucket": "normal",
        "player_count": 1,
        "objective_score_proxy": 0,
        "objective_score_proxy_mode": "exact",
        "kills_per_minute": 0.0,
        "combat_per_minute": 0.0,
        "support_per_minute": 0.0,
        "objective_proxy_per_minute": 0.0,
        "participation_bucket": "full",
        "participation_mode": "exact",
        "participation_quality_score": 1.0,
        "capabilities": {"test": True},
    }


if __name__ == "__main__":
    unittest.main()
