"""Manual ingestion of Hell Let Loose RCON AdminLog events."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

from .config import get_rcon_request_timeout_seconds
from .rcon_admin_log_storage import (
    list_rcon_admin_log_event_counts,
    persist_rcon_admin_log_entries,
)
from .rcon_client import HllRconConnection, RconServerTarget, build_rcon_target_key, load_rcon_targets


@dataclass(slots=True)
class AdminLogIngestionStats:
    targets_seen: int = 0
    events_seen: int = 0
    events_inserted: int = 0
    duplicate_events: int = 0
    failed_targets: int = 0


def ingest_rcon_admin_logs(
    *,
    minutes: int,
    target_key: str | None = None,
) -> dict[str, object]:
    """Fetch and persist recent AdminLog entries from configured RCON targets."""
    selected_targets = _select_targets(target_key)
    stats = AdminLogIngestionStats()
    targets: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    timeout_seconds = get_rcon_request_timeout_seconds()

    for target in selected_targets:
        stats.targets_seen += 1
        target_metadata = serialize_rcon_target(target)

        try:
            normalized_entries = fetch_recent_admin_log_entries(
                target,
                lookback_seconds=minutes * 60,
                timeout_seconds=timeout_seconds,
            )
            delta = persist_rcon_admin_log_entries(
                target=target_metadata,
                entries=normalized_entries,
            )

            stats.events_seen += int(delta["events_seen"])
            stats.events_inserted += int(delta["events_inserted"])
            stats.duplicate_events += int(delta["duplicate_events"])
            targets.append(
                {
                    **target_metadata,
                    "status": "ok",
                    "minutes": minutes,
                    **delta,
                }
            )
        except Exception as exc:  # noqa: BLE001 - manual diagnostic command reports per-target failures
            stats.failed_targets += 1
            errors.append(
                {
                    **target_metadata,
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

    return {
        "status": "ok" if not errors else ("partial" if targets else "error"),
        "target_scope": target_key or "all-configured-rcon-targets",
        "minutes": minutes,
        "targets": targets,
        "errors": errors,
        "totals": {
            "targets_seen": stats.targets_seen,
            "events_seen": stats.events_seen,
            "events_inserted": stats.events_inserted,
            "duplicate_events": stats.duplicate_events,
            "failed_targets": stats.failed_targets,
        },
        "event_counts": list_rcon_admin_log_event_counts(),
    }


def _select_targets(target_key: str | None) -> list[object]:
    configured_targets = list(load_rcon_targets())
    if not configured_targets:
        raise RuntimeError("No RCON targets configured in HLL_BACKEND_RCON_TARGETS.")
    if target_key is None:
        return configured_targets

    normalized = target_key.strip()
    selected = [
        target
        for target in configured_targets
        if build_rcon_target_key(target) == normalized
    ]
    if not selected:
        raise ValueError(f"Unknown RCON target key: {target_key}")
    return selected


def fetch_recent_admin_log_entries(
    target: RconServerTarget,
    *,
    lookback_seconds: int,
    timeout_seconds: float | None = None,
) -> list[dict[str, object]]:
    """Fetch recent raw AdminLog entries for one configured target."""
    if lookback_seconds <= 0:
        raise ValueError("lookback_seconds must be positive.")
    resolved_timeout = (
        get_rcon_request_timeout_seconds() if timeout_seconds is None else timeout_seconds
    )
    with HllRconConnection(timeout_seconds=resolved_timeout) as connection:
        connection.connect(host=target.host, port=target.port, password=target.password)
        payload = connection.execute_json(
            "GetAdminLog",
            {
                "LogBackTrackTime": lookback_seconds,
                "Filters": [],
            },
        )
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def serialize_rcon_target(target: object) -> dict[str, object]:
    return {
        "target_key": build_rcon_target_key(target),
        "external_server_id": target.external_server_id,
        "name": target.name,
        "host": target.host,
        "port": target.port,
        "source_name": target.source_name,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=int, default=60)
    parser.add_argument("--target", default=None)
    args = parser.parse_args()

    print(
        json.dumps(
            ingest_rcon_admin_logs(minutes=args.minutes, target_key=args.target),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
