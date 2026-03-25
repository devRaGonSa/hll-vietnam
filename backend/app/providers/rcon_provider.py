"""RCON provider adapter for live HLL server state."""

from __future__ import annotations

from dataclasses import dataclass

from ..rcon_client import (
    RconServerTarget,
    load_rcon_targets,
    query_live_server_sample,
)
from ..snapshots import build_snapshot_batch, utc_now
from ..storage import persist_snapshot_batch


@dataclass(frozen=True, slots=True)
class RconLiveDataSource:
    """Live provider backed by direct HLL RCON access."""

    source_kind: str = "rcon"

    def collect_snapshots(self, *, persist: bool) -> dict[str, object]:
        configured_targets = load_rcon_targets()
        if not configured_targets:
            raise RuntimeError("No RCON targets configured in HLL_BACKEND_RCON_TARGETS.")

        captured_at = utc_now()
        normalized_records: list[dict[str, object]] = []
        errors: list[dict[str, object]] = []

        for target in configured_targets:
            try:
                normalized_records.append(query_live_server_sample(target)["normalized"])
            except Exception as error:  # noqa: BLE001 - keep provider failures controlled
                errors.append(
                    {
                        "target": target.name,
                        "host": target.host,
                        "port": target.port,
                        "message": str(error),
                    }
                )

        payload = {
            "source_name": "hll-rcon",
            "collection_mode": "rcon",
            "fallback_used": False,
            "target_count": len(configured_targets),
            "success_count": len(normalized_records),
            "errors": errors,
            "captured_at": captured_at.isoformat().replace("+00:00", "Z"),
            "snapshots": build_snapshot_batch(normalized_records, captured_at=captured_at),
        }
        if persist:
            payload["storage"] = persist_snapshot_batch(
                payload["snapshots"],
                source_name=payload["source_name"],
                captured_at=payload["captured_at"],
            )
        return payload

    def build_target_index(self) -> dict[str | None, RconServerTarget]:
        return {
            target.external_server_id: target
            for target in load_rcon_targets()
            if target.external_server_id
        }
