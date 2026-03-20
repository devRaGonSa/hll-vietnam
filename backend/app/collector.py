"""Minimal collector bootstrap for provisional server snapshots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable, Mapping, Sequence

from .a2s_client import DEFAULT_A2S_TIMEOUT, query_server_info
from .normalizers import normalize_a2s_server_info, normalize_server_record
from .server_targets import A2SServerTarget, load_a2s_targets
from .snapshots import build_snapshot_batch, utc_now
from .storage import persist_snapshot_batch


RawSourceFetcher = Callable[[], Sequence[Mapping[str, object]]]
TargetProbe = Callable[[A2SServerTarget, float], Mapping[str, object]]


CONTROLLED_RAW_SERVER_SOURCE: tuple[dict[str, object], ...] = (
    {
        "external_server_id": "hll-esp-tactical-rotation",
        "server_name": "HLL ESP Tactical Rotation",
        "status": "online",
        "players": 74,
        "max_players": 100,
        "current_map": "Sainte-Marie-du-Mont",
        "region": "EU",
    },
    {
        "external_server_id": "hll-latam-night-offensive",
        "server_name": "HLL LATAM Night Offensive",
        "status": "online",
        "players": 51,
        "max_players": 100,
        "current_map": "Carentan",
        "region": "LATAM",
    },
    {
        "external_server_id": "hll-community-reserve",
        "server_name": "HLL Community Reserve",
        "status": "offline",
        "players": 0,
        "max_players": 100,
        "current_map": None,
        "region": "EU",
    },
)


def fetch_controlled_server_source() -> Sequence[Mapping[str, object]]:
    """Return the controlled development source used by the collector bootstrap."""
    return CONTROLLED_RAW_SERVER_SOURCE


def fetch_a2s_probe(
    host: str,
    query_port: int,
    *,
    timeout: float = DEFAULT_A2S_TIMEOUT,
    source_name: str = "a2s-info",
    external_server_id: str | None = None,
    region: str | None = None,
) -> dict[str, object]:
    """Probe one A2S target and normalize its metadata for the collector model."""
    server_info = query_server_info(host, query_port, timeout=timeout)
    return normalize_a2s_server_info(
        server_info,
        source_name=source_name,
        external_server_id=external_server_id,
        region=region,
    )


def fetch_configured_a2s_probes(
    *,
    timeout: float = DEFAULT_A2S_TIMEOUT,
    probe_target: TargetProbe | None = None,
) -> tuple[dict[str, object], ...]:
    """Probe the configured A2S targets without hardcoding them in collector logic."""
    probe = probe_target or _probe_configured_target
    return tuple(
        dict(probe(target, timeout))
        for target in load_a2s_targets()
    )


def collect_server_snapshots(
    *,
    fetch_raw_source: RawSourceFetcher = fetch_controlled_server_source,
    source_name: str = "controlled-placeholder",
    source_mode: str = "controlled",
    timeout: float = DEFAULT_A2S_TIMEOUT,
    allow_controlled_fallback: bool = True,
    probe_target: TargetProbe | None = None,
    persist: bool = False,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Collect snapshot batches from controlled data, A2S, or auto mode."""
    normalized_records, collection_details = _collect_normalized_records(
        fetch_raw_source=fetch_raw_source,
        source_name=source_name,
        source_mode=source_mode,
        timeout=timeout,
        allow_controlled_fallback=allow_controlled_fallback,
        probe_target=probe_target,
    )
    captured_at = utc_now()

    payload = {
        "source_name": collection_details["source_name"],
        "collection_mode": collection_details["collection_mode"],
        "fallback_used": collection_details["fallback_used"],
        "target_count": collection_details["target_count"],
        "success_count": collection_details["success_count"],
        "errors": collection_details["errors"],
        "captured_at": captured_at.isoformat().replace("+00:00", "Z"),
        "snapshots": build_snapshot_batch(
            normalized_records,
            captured_at=captured_at,
        ),
    }
    if persist:
        payload["storage"] = persist_snapshot_batch(
            payload["snapshots"],
            source_name=payload["source_name"],
            captured_at=payload["captured_at"],
            db_path=db_path,
        )

    return payload


def main() -> None:
    """Allow manual collector execution during development."""
    parser = argparse.ArgumentParser(description="Collect development server snapshots.")
    parser.add_argument(
        "--source",
        choices=("controlled", "a2s", "auto"),
        default="auto",
        help="Choose controlled data, configured A2S targets, or auto with fallback.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_A2S_TIMEOUT,
        help="Socket timeout in seconds for A2S probes.",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Disable fallback to controlled data when A2S fails.",
    )
    args = parser.parse_args()

    payload = collect_server_snapshots(
        source_mode=args.source,
        timeout=args.timeout,
        allow_controlled_fallback=not args.no_fallback,
        persist=True,
    )
    print(json.dumps(payload, indent=2))


def _collect_normalized_records(
    *,
    fetch_raw_source: RawSourceFetcher,
    source_name: str,
    source_mode: str,
    timeout: float,
    allow_controlled_fallback: bool,
    probe_target: TargetProbe | None,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    if source_mode == "controlled":
        raw_records = fetch_raw_source()
        return (
            [
                normalize_server_record(record, source_name=source_name)
                for record in raw_records
            ],
            {
                "source_name": source_name,
                "collection_mode": "controlled",
                "fallback_used": False,
                "target_count": 0,
                "success_count": 0,
                "errors": [],
            },
        )

    configured_targets = load_a2s_targets()
    records: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    probe = probe_target or _probe_configured_target

    for target in configured_targets:
        try:
            records.append(dict(probe(target, timeout)))
        except Exception as error:  # noqa: BLE001 - keep collector failures controlled
            errors.append(
                {
                    "target": target.name,
                    "host": target.host,
                    "query_port": target.query_port,
                    "message": str(error),
                }
            )

    if records:
        return (
            records,
            {
                "source_name": "a2s-info",
                "collection_mode": "a2s",
                "fallback_used": False,
                "target_count": len(configured_targets),
                "success_count": len(records),
                "errors": errors,
            },
        )

    if source_mode == "a2s" or not allow_controlled_fallback:
        return (
            [],
            {
                "source_name": "a2s-info",
                "collection_mode": "a2s",
                "fallback_used": False,
                "target_count": len(configured_targets),
                "success_count": 0,
                "errors": errors,
            },
        )

    raw_records = fetch_raw_source()
    normalized_records = [
        normalize_server_record(record, source_name=source_name)
        for record in raw_records
    ]
    return (
        normalized_records,
        {
            "source_name": source_name,
            "collection_mode": "controlled-fallback",
            "fallback_used": True,
            "target_count": len(configured_targets),
            "success_count": 0,
            "errors": errors,
        },
    )


def _probe_configured_target(
    target: A2SServerTarget,
    timeout: float,
) -> dict[str, object]:
    return fetch_a2s_probe(
        target.host,
        target.query_port,
        timeout=timeout,
        source_name=target.source_name,
        external_server_id=target.external_server_id,
        region=target.region,
    )


if __name__ == "__main__":
    main()
