"""Read-only forensic audit for historical RCON match materialization.

The tool deliberately avoids repository storage helpers because several nominal
read paths initialize schemas or populate caches. It emits aggregate evidence
only: no player identity, chat, raw AdminLog message, host, credential, DSN or
authenticated URL is serialized.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import heapq
import json
import os
import re
import sqlite3
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.normalizers import normalize_map_name  # noqa: E402
from app.rcon_admin_log_parser import parse_rcon_admin_log_entry  # noqa: E402


SCHEMA_VERSION = "task-287.audit.v1"
TRUSTED_SERVERS = {
    "comunidad-hispana-01": "Comunidad Hispana #01",
    "comunidad-hispana-02": "Comunidad Hispana #02",
}
ELIGIBLE_EVENT_TYPES = ("kill", "team_switch", "connected", "disconnected", "chat")
BOUNDARY_TYPES = ("match_start", "match_end")
MATERIALIZED_SOURCE_END = "admin-log-match-ended"
FORBIDDEN_SQL_RE = re.compile(
    r"\b(?:INSERT|UPDATE|DELETE|TRUNCATE|ALTER|CREATE|DROP|VACUUM|REINDEX|REPLACE|MERGE|CALL|COPY)\b",
    re.IGNORECASE,
)
ALLOWED_SQL_PREFIXES = ("SELECT", "WITH", "EXPLAIN")
PREFIX_RE = re.compile(r"^\[(?P<relative>.*?) \((?P<server_time>\d+)\)\] (?P<body>.*)$")
STORAGE_PREFIX_RE = re.compile(r"^\[.*?\(\d+\)\]\s+", re.DOTALL)
MATCH_START_RELAXED_RE = re.compile(r"\bMATCH\s+START\b", re.IGNORECASE)
MATCH_END_RELAXED_RE = re.compile(r"\bMATCH\s+END(?:ED)?\b", re.IGNORECASE)
TEAM_KILL_RELAXED_RE = re.compile(r"\bTEAM\s+KILL\b", re.IGNORECASE)
SENSITIVE_OUTPUT_KEYS = {
    "raw_message",
    "canonical_message",
    "raw_entry_json",
    "raw_payload_json",
    "parsed_payload_json",
    "player_id",
    "player_name",
    "steam_id",
    "target_key",
    "host",
    "password",
    "dsn",
    "database_url",
    "chat_message",
}


def parse_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def iso_timestamp(value: object) -> str | None:
    parsed = parse_timestamp(value)
    return parsed.isoformat().replace("+00:00", "Z") if parsed else None


def server_time_timestamp(value: object) -> datetime | None:
    """Return a UTC wall clock only when server_time is a plausible Unix epoch."""

    if value is None:
        return None
    try:
        epoch_seconds = int(value)
    except (TypeError, ValueError):
        return None
    # Avoid treating a reset counter or relative clock as a calendar timestamp.
    if not 946_684_800 <= epoch_seconds <= 4_102_444_800:
        return None
    try:
        return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def match_time_bounds(match: Mapping[str, object]) -> tuple[datetime | None, datetime | None]:
    """Prefer boundary server_time over ingestion/batch timestamps for correlation."""

    return (
        server_time_timestamp(match.get("started_server_time"))
        or parse_timestamp(match.get("started_at")),
        server_time_timestamp(match.get("ended_server_time"))
        or parse_timestamp(match.get("ended_at")),
    )


def count_ordered_boundary_pairs(
    boundaries: Iterable[tuple[datetime, int, str]],
) -> int:
    """Count only sequence-valid START→END pairs; orphan ends never pair backward."""

    pair_count = 0
    open_start = False
    for _, _, event_type in sorted(boundaries):
        if event_type == "match_start":
            open_start = True
        elif event_type == "match_end" and open_start:
            pair_count += 1
            open_start = False
    return pair_count


def safe_ref(prefix: str, value: object, *, length: int = 12) -> str:
    digest = hashlib.sha256(str(value).encode("utf-8", errors="replace")).hexdigest()[:length]
    return f"{prefix}-{digest}"


def json_object(value: object) -> dict[str, object]:
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def as_int(value: object, default: int = 0) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def ensure_read_only_sql(sql: str) -> None:
    stripped = sql.strip()
    if not stripped:
        raise ValueError("empty SQL is not allowed")
    if FORBIDDEN_SQL_RE.search(stripped):
        raise ValueError("mutating SQL rejected by forensic audit guard")
    without_trailing_semicolon = stripped[:-1].rstrip() if stripped.endswith(";") else stripped
    if ";" in without_trailing_semicolon:
        raise ValueError("multiple SQL statements are not allowed")
    first = stripped.split(None, 1)[0].upper()
    if first == "PRAGMA":
        if "=" in stripped or not re.fullmatch(
            r"PRAGMA\s+(?:table_info|index_list|index_info)\s*\([^;]+\)\s*;?",
            stripped,
            flags=re.IGNORECASE,
        ):
            raise ValueError("non-metadata PRAGMA rejected by forensic audit guard")
        return
    if first == "SHOW":
        if not re.fullmatch(r"SHOW\s+transaction_read_only\s*;?", stripped, flags=re.IGNORECASE):
            raise ValueError("SHOW statement rejected by forensic audit guard")
        return
    if first not in ALLOWED_SQL_PREFIXES:
        raise ValueError(f"SQL prefix {first!r} is not allowlisted")


def canonicalize_admin_message(raw_message: object) -> str:
    normalized = str(raw_message or "").strip()
    return STORAGE_PREFIX_RE.sub("", normalized).strip()


def assert_public_result_is_sanitized(value: object, *, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = str(key).strip().lower()
            if normalized_key in SENSITIVE_OUTPUT_KEYS:
                raise ValueError(f"sensitive output key rejected at {path}")
            assert_public_result_is_sanitized(child, path=f"{path}.{normalized_key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            assert_public_result_is_sanitized(child, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        lowered = value.lower()
        if "postgresql://" in lowered or "postgres://" in lowered:
            raise ValueError(f"connection string rejected at {path}")


class ReadOnlyDatabase:
    def __init__(self, connection: Any, dialect: str, source_ref: str) -> None:
        self.connection = connection
        self.dialect = dialect
        self.source_ref = source_ref

    def _adapt(self, sql: str) -> str:
        return sql if self.dialect == "sqlite" else sql.replace("?", "%s")

    def execute(self, sql: str, params: Sequence[object] = ()) -> Any:
        ensure_read_only_sql(sql)
        return self.connection.execute(self._adapt(sql), tuple(params))

    def rows(self, sql: str, params: Sequence[object] = ()) -> list[dict[str, object]]:
        cursor = self.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def iterate(
        self,
        sql: str,
        params: Sequence[object] = (),
        *,
        batch_size: int = 5_000,
    ) -> Iterator[dict[str, object]]:
        cursor = self.execute(sql, params)
        while True:
            batch = cursor.fetchmany(batch_size)
            if not batch:
                break
            for row in batch:
                yield dict(row)

    def table_exists(self, table: str) -> bool:
        if self.dialect == "sqlite":
            row = self.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
                (table,),
            ).fetchone()
        else:
            row = self.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = current_schema() AND table_name = ? LIMIT 1",
                (table,),
            ).fetchone()
        return row is not None

    def close(self) -> None:
        try:
            self.connection.rollback()
        finally:
            self.connection.close()


def open_sqlite_read_only(path: Path, *, immutable: bool) -> ReadOnlyDatabase:
    resolved = path.resolve(strict=True)
    query = "mode=ro"
    if immutable:
        query += "&immutable=1"
    connection = sqlite3.connect(
        resolved.as_uri() + "?" + query,
        uri=True,
        timeout=30,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    if connection.execute("PRAGMA query_only").fetchone()[0] != 1:
        connection.close()
        raise RuntimeError("SQLite query_only could not be enabled")
    connection.execute("BEGIN")
    source_ref = safe_ref("sqlite", f"{resolved.name}:{resolved.stat().st_size}")
    return ReadOnlyDatabase(connection, "sqlite", source_ref)


def open_postgres_read_only(env_name: str) -> ReadOnlyDatabase:
    dsn = os.environ.get(env_name)
    if not dsn:
        raise RuntimeError(f"PostgreSQL environment variable {env_name!r} is not set")
    try:
        import psycopg
        from psycopg.rows import dict_row

        connection = psycopg.connect(
            dsn,
            autocommit=True,
            row_factory=dict_row,
            options="-c default_transaction_read_only=on",
        )
        connection.execute("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        read_only = connection.execute("SHOW transaction_read_only").fetchone()["transaction_read_only"]
    except Exception as error:  # Never include driver text; it may contain a DSN.
        raise RuntimeError("PostgreSQL read-only connection failed") from None
    if str(read_only).lower() not in {"on", "true", "1"}:
        connection.rollback()
        connection.close()
        raise RuntimeError("PostgreSQL transaction is not read-only")
    return ReadOnlyDatabase(connection, "postgres", "postgres-production-redacted")


def read_env_value(path: Path | None, name: str) -> str | None:
    if path is None or not path.exists():
        return None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip()
    return None


@dataclass
class TargetResolver:
    key_to_slug: dict[str, str]
    target_id_to_slug: dict[int, str]
    target_id_to_key: dict[int, str]
    historical_server_id_to_slug: dict[int, str]

    def resolve(self, target_key: object, external_server_id: object = None) -> str | None:
        external = str(external_server_id or "").strip()
        key = str(target_key or "").strip()
        if external in TRUSTED_SERVERS:
            return external
        if key in TRUSTED_SERVERS:
            return key
        return self.key_to_slug.get(key)


def build_target_resolver(db: ReadOnlyDatabase, env_path: Path | None) -> TargetResolver:
    key_to_slug = {slug: slug for slug in TRUSTED_SERVERS}
    target_id_to_slug: dict[int, str] = {}
    target_id_to_key: dict[int, str] = {}
    historical_server_id_to_slug: dict[int, str] = {}

    configured_pairs: dict[tuple[str, int], str] = {}
    encoded = read_env_value(env_path, "HLL_BACKEND_RCON_TARGETS")
    if encoded:
        try:
            targets = json.loads(encoded)
        except (TypeError, ValueError, json.JSONDecodeError):
            targets = []
        if isinstance(targets, list):
            for item in targets:
                if not isinstance(item, dict):
                    continue
                slug = str(item.get("slug") or "").strip()
                host = str(item.get("host") or "").strip()
                port = as_int(item.get("port"), -1)
                if slug in TRUSTED_SERVERS and host and port >= 0:
                    configured_pairs[(host, port)] = slug
                    key_to_slug[f"rcon:{host}:{port}"] = slug

    if db.table_exists("rcon_historical_targets"):
        rows = db.rows(
            "SELECT id, target_key, external_server_id, display_name, host, port "
            "FROM rcon_historical_targets ORDER BY id"
        )
        for row in rows:
            target_id = as_int(row.get("id"), -1)
            target_key = str(row.get("target_key") or "")
            slug = str(row.get("external_server_id") or "")
            if slug not in TRUSTED_SERVERS:
                slug = configured_pairs.get(
                    (str(row.get("host") or ""), as_int(row.get("port"), -1)),
                    "",
                )
            if slug in TRUSTED_SERVERS:
                key_to_slug[target_key] = slug
                target_id_to_slug[target_id] = slug
                target_id_to_key[target_id] = target_key

    if db.table_exists("historical_servers"):
        for row in db.rows("SELECT id, slug FROM historical_servers ORDER BY id"):
            slug = str(row.get("slug") or "")
            if slug in TRUSTED_SERVERS:
                historical_server_id_to_slug[as_int(row.get("id"), -1)] = slug

    return TargetResolver(
        key_to_slug=key_to_slug,
        target_id_to_slug=target_id_to_slug,
        target_id_to_key=target_id_to_key,
        historical_server_id_to_slug=historical_server_id_to_slug,
    )


def empty_server_result(slug: str) -> dict[str, object]:
    return {
        "display_name": TRUSTED_SERVERS[slug],
        "admin_log": {},
        "coverage": {},
        "materialized": {},
        "competitive_windows": {},
        "scoreboard": {},
    }


def audit_inventory(
    db: ReadOnlyDatabase,
    resolver: TargetResolver,
    selected_servers: set[str],
) -> tuple[dict[str, dict[str, object]], set[str]]:
    servers = {slug: empty_server_result(slug) for slug in sorted(selected_servers)}
    event_target_keys: set[str] = set()
    rows = db.rows(
        """
        SELECT target_key, external_server_id,
               COUNT(*) AS total_events,
               SUM(CASE WHEN event_type = 'kill' THEN 1 ELSE 0 END) AS kill_events,
               SUM(CASE WHEN event_type = 'match_start' THEN 1 ELSE 0 END) AS match_start,
               SUM(CASE WHEN event_type = 'match_end' THEN 1 ELSE 0 END) AS match_end,
               SUM(CASE WHEN event_type = 'unknown' THEN 1 ELSE 0 END) AS unknown_events,
               SUM(CASE WHEN event_type = 'connected' THEN 1 ELSE 0 END) AS connected,
               SUM(CASE WHEN event_type = 'disconnected' THEN 1 ELSE 0 END) AS disconnected,
               SUM(CASE WHEN event_type = 'team_switch' THEN 1 ELSE 0 END) AS team_switch,
               SUM(CASE WHEN server_time IS NULL THEN 1 ELSE 0 END) AS null_server_time,
               MIN(server_time) AS min_server_time,
               MAX(server_time) AS max_server_time,
               MIN(event_timestamp) AS min_event_timestamp,
               MAX(event_timestamp) AS max_event_timestamp,
               MIN(created_at) AS min_created_at,
               MAX(created_at) AS max_created_at
        FROM rcon_admin_log_events
        GROUP BY target_key, external_server_id
        ORDER BY target_key, external_server_id
        """
    )
    count_fields = (
        "total_events",
        "kill_events",
        "match_start",
        "match_end",
        "unknown_events",
        "connected",
        "disconnected",
        "team_switch",
        "null_server_time",
    )
    for row in rows:
        slug = resolver.resolve(row.get("target_key"), row.get("external_server_id"))
        if slug not in selected_servers:
            continue
        target_key = str(row.get("target_key") or "")
        event_target_keys.add(target_key)
        admin = servers[slug]["admin_log"]
        for field in count_fields:
            admin[field] = as_int(admin.get(field)) + as_int(row.get(field))
        coverage = servers[slug]["coverage"]
        coverage.setdefault("server_time_ranges", []).append(
            [row.get("min_server_time"), row.get("max_server_time")]
        )
        coverage.setdefault("event_timestamp_ranges", []).append(
            [iso_timestamp(row.get("min_event_timestamp")), iso_timestamp(row.get("max_event_timestamp"))]
        )
        coverage.setdefault("created_at_ranges", []).append(
            [iso_timestamp(row.get("min_created_at")), iso_timestamp(row.get("max_created_at"))]
        )
    return servers, event_target_keys


def audit_requested_event_range(
    db: ReadOnlyDatabase,
    resolver: TargetResolver,
    selected_servers: set[str],
    from_timestamp: datetime | None,
    until_timestamp: datetime | None,
) -> dict[str, object] | None:
    if from_timestamp is None and until_timestamp is None:
        return None
    clauses: list[str] = []
    params: list[object] = []
    if from_timestamp is not None:
        clauses.append("event_timestamp >= ?")
        params.append(from_timestamp.isoformat().replace("+00:00", "Z"))
    if until_timestamp is not None:
        clauses.append("event_timestamp < ?")
        params.append(until_timestamp.isoformat().replace("+00:00", "Z"))
    rows = db.rows(
        "SELECT target_key, external_server_id, COUNT(*) AS total_events, "
        "SUM(CASE WHEN event_type = 'kill' THEN 1 ELSE 0 END) AS kill_events, "
        "SUM(CASE WHEN event_type = 'match_start' THEN 1 ELSE 0 END) AS match_start, "
        "SUM(CASE WHEN event_type = 'match_end' THEN 1 ELSE 0 END) AS match_end, "
        "MIN(event_timestamp) AS first_event_timestamp, "
        "MAX(event_timestamp) AS last_event_timestamp "
        "FROM rcon_admin_log_events WHERE "
        + " AND ".join(clauses)
        + " GROUP BY target_key, external_server_id ORDER BY target_key",
        params,
    )
    result: dict[str, Counter[str]] = {slug: Counter() for slug in selected_servers}
    coverage: dict[str, list[str | None]] = {
        slug: [None, None] for slug in selected_servers
    }
    for row in rows:
        slug = resolver.resolve(row.get("target_key"), row.get("external_server_id"))
        if slug not in selected_servers:
            continue
        for field in ("total_events", "kill_events", "match_start", "match_end"):
            result[slug][field] += as_int(row.get(field))
        first = iso_timestamp(row.get("first_event_timestamp"))
        last = iso_timestamp(row.get("last_event_timestamp"))
        coverage[slug][0] = min(filter(None, (coverage[slug][0], first)), default=None)
        coverage[slug][1] = max(filter(None, (coverage[slug][1], last)), default=None)
    return {
        slug: {**dict(result[slug]), "coverage": coverage[slug]}
        for slug in sorted(selected_servers)
    }


def payload_map(payload: Mapping[str, object]) -> str | None:
    value = payload.get("map_name") or payload.get("map") or payload.get("current_map")
    return str(value).strip() if value is not None and str(value).strip() else None


def build_match_key(
    target_key: str,
    started_server_time: object,
    ended_server_time: object,
    map_name: object,
) -> str:
    map_part = "".join(character.lower() for character in str(map_name or "unknown") if character.isalnum())
    start_part = "missing" if started_server_time is None else str(started_server_time)
    end_part = "open" if ended_server_time is None else str(ended_server_time)
    return f"{target_key}:{start_part}:{end_part}:{map_part}"


def make_derived_match(start: dict[str, object] | None, end: dict[str, object] | None) -> dict[str, object]:
    if start is None and end is None:
        raise ValueError("a derived match requires a boundary")
    start_payload = json_object(start.get("parsed_payload_json") if start else None)
    end_payload = json_object(end.get("parsed_payload_json") if end else None)
    source = end or start or {}
    target_key = str(source.get("target_key") or "")
    started_server_time = start.get("server_time") if start else None
    ended_server_time = end.get("server_time") if end else None
    map_name = payload_map(end_payload) or payload_map(start_payload)
    return {
        "target_key": target_key,
        "external_server_id": source.get("external_server_id"),
        "match_key": build_match_key(target_key, started_server_time, ended_server_time, map_name),
        "map_name": map_name,
        "game_mode": start_payload.get("game_mode"),
        "started_server_time": started_server_time,
        "ended_server_time": ended_server_time,
        "started_at": start.get("event_timestamp") if start else None,
        "ended_at": end.get("event_timestamp") if end else None,
        "allied_score": end_payload.get("allied_score"),
        "axis_score": end_payload.get("axis_score"),
        "confidence_mode": "exact" if end else "partial",
        "source_basis": MATERIALIZED_SOURCE_END if end else "admin-log-match-start",
        "start_event_id": start.get("id") if start else None,
        "end_event_id": end.get("id") if end else None,
    }


def derive_admin_matches(
    boundary_rows: Iterable[dict[str, object]],
    resolver: TargetResolver,
    selected_servers: set[str],
    *,
    nulls_last: bool = False,
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    def boundary_sort_key(row: Mapping[str, object]) -> tuple[object, ...]:
        server_time = row.get("server_time")
        null_rank = int(server_time is None) if nulls_last else int(server_time is not None)
        return (
            str(row.get("target_key") or ""),
            null_rank,
            0 if server_time is None else as_int(server_time),
            as_int(row.get("id")),
        )

    ordered = sorted(
        boundary_rows,
        key=boundary_sort_key,
    )
    open_by_target: dict[str, dict[str, object]] = {}
    matches: list[dict[str, object]] = []
    summaries: dict[str, Counter[str]] = {slug: Counter() for slug in selected_servers}
    examples: dict[str, dict[str, list[dict[str, object]]]] = {
        slug: defaultdict(list) for slug in selected_servers
    }

    def record(slug: str, label: str, *rows: Mapping[str, object]) -> None:
        values = examples[slug][label]
        if len(values) >= 5:
            return
        values.append(
            {
                "event_refs": [safe_ref("event", row.get("id")) for row in rows],
                "server_times": [row.get("server_time") for row in rows],
            }
        )

    for row in ordered:
        slug = resolver.resolve(row.get("target_key"), row.get("external_server_id"))
        if slug not in selected_servers:
            continue
        target_key = str(row.get("target_key") or "")
        event_type = str(row.get("event_type") or "")
        if event_type == "match_start":
            if target_key in open_by_target:
                summaries[slug]["consecutive_start"] += 1
                previous_start = open_by_target.pop(target_key)
                record(slug, "consecutive_start", previous_start, row)
                matches.append(make_derived_match(previous_start, None))
            open_by_target[target_key] = row
            continue
        start = open_by_target.pop(target_key, None)
        if start is None:
            summaries[slug]["orphan_end"] += 1
            record(slug, "orphan_end", row)
        else:
            summaries[slug]["normal_start_end"] += 1
            start_map = payload_map(json_object(start.get("parsed_payload_json")))
            end_map = payload_map(json_object(row.get("parsed_payload_json")))
            if normalize_map_name(start_map) != normalize_map_name(end_map):
                summaries[slug]["normalized_map_mismatch"] += 1
                record(slug, "normalized_map_mismatch", start, row)
            elif str(start_map or "") != str(end_map or ""):
                summaries[slug]["raw_map_identity_difference"] += 1
                record(slug, "raw_map_identity_difference", start, row)
        matches.append(make_derived_match(start, row))
    for target_key, start in sorted(open_by_target.items()):
        slug = resolver.resolve(target_key, start.get("external_server_id"))
        if slug in selected_servers:
            summaries[slug]["final_open_start"] += 1
            record(slug, "final_open_start", start)
            matches.append(make_derived_match(start, None))
    result: dict[str, dict[str, object]] = {}
    sequence_fields = (
        "normal_start_end",
        "consecutive_start",
        "orphan_end",
        "final_open_start",
        "normalized_map_mismatch",
        "raw_map_identity_difference",
    )
    for slug, counter in sorted(summaries.items()):
        result[slug] = {field: counter.get(field, 0) for field in sequence_fields}
        result[slug]["sanitized_examples"] = {
            label: values for label, values in sorted(examples[slug].items())
        }
    return matches, result


def bound_class(match: Mapping[str, object]) -> str:
    lower = match.get("started_server_time")
    upper = match.get("ended_server_time")
    if lower is not None and upper is not None:
        return "both_bounds"
    if lower is not None:
        return "lower_only"
    if upper is not None:
        return "upper_only"
    return "no_bounds"


def read_boundaries(
    db: ReadOnlyDatabase,
    resolver: TargetResolver,
    selected_servers: set[str],
) -> list[dict[str, object]]:
    rows = db.rows(
        """
        SELECT id, target_key, external_server_id, event_timestamp, server_time,
               event_type, parsed_payload_json, canonical_message, created_at
        FROM rcon_admin_log_events
        WHERE event_type IN ('match_start', 'match_end')
        ORDER BY target_key, server_time, id
        """
    )
    return [
        row
        for row in rows
        if resolver.resolve(row.get("target_key"), row.get("external_server_id")) in selected_servers
    ]


def audit_boundary_ordering(
    rows: list[dict[str, object]],
    resolver: TargetResolver,
    selected_servers: set[str],
) -> dict[str, dict[str, object]]:
    results = {slug: Counter() for slug in selected_servers}
    examples: dict[str, dict[str, list[dict[str, object]]]] = {
        slug: defaultdict(list) for slug in selected_servers
    }
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    duplicate_groups: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    same_time_groups: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("target_key") or "")].append(row)
        duplicate_groups[
            (
                row.get("target_key"),
                row.get("server_time"),
                row.get("event_type"),
                row.get("canonical_message"),
            )
        ].append(row)
        same_time_groups[(row.get("target_key"), row.get("server_time"))].append(row)
    for target_key, target_rows in grouped.items():
        slug = resolver.resolve(target_key, target_rows[0].get("external_server_id"))
        if slug not in selected_servers:
            continue
        for field in ("created_at", "event_timestamp"):
            ordered = sorted(
                target_rows,
                key=lambda row: (
                    parse_timestamp(row.get(field)) or datetime.min.replace(tzinfo=timezone.utc),
                    as_int(row.get("id")),
                ),
            )
            previous: int | None = None
            previous_row: dict[str, object] | None = None
            for row in ordered:
                current = row.get("server_time")
                if current is None:
                    continue
                current_int = as_int(current)
                if previous is not None and current_int < previous:
                    results[slug][f"server_time_decrease_by_{field}"] += 1
                    label = f"server_time_decrease_by_{field}"
                    if len(examples[slug][label]) < 5:
                        examples[slug][label].append(
                            {
                                "event_refs": [
                                    safe_ref("event", previous_row.get("id")) if previous_row else None,
                                    safe_ref("event", row.get("id")),
                                ],
                                "server_times": [previous, current_int],
                            }
                        )
                previous = current_int
                previous_row = row
    for key, duplicate_rows in duplicate_groups.items():
        if len(duplicate_rows) <= 1:
            continue
        slug = resolver.resolve(key[0])
        if slug in selected_servers:
            results[slug]["duplicate_boundary_groups"] += 1
            results[slug]["duplicate_boundary_extra_rows"] += len(duplicate_rows) - 1
            if len(examples[slug]["duplicate_boundary_group"]) < 5:
                examples[slug]["duplicate_boundary_group"].append(
                    {
                        "event_refs": [safe_ref("event", row.get("id")) for row in duplicate_rows[:5]],
                        "server_time": key[1],
                    }
                )
    for key, collision_rows in same_time_groups.items():
        if len(collision_rows) <= 1:
            continue
        slug = resolver.resolve(key[0])
        if slug in selected_servers:
            results[slug]["same_server_time_boundary_groups"] += 1
            results[slug]["same_server_time_boundary_extra_rows"] += len(collision_rows) - 1
            if len(examples[slug]["same_server_time_boundary_group"]) < 5:
                examples[slug]["same_server_time_boundary_group"].append(
                    {
                        "event_refs": [safe_ref("event", row.get("id")) for row in collision_rows[:5]],
                        "server_time": key[1],
                    }
                )
    ordering_fields = (
        "server_time_decrease_by_created_at",
        "server_time_decrease_by_event_timestamp",
        "duplicate_boundary_groups",
        "duplicate_boundary_extra_rows",
        "same_server_time_boundary_groups",
        "same_server_time_boundary_extra_rows",
    )
    return {
        slug: {
            **{field: counter.get(field, 0) for field in ordering_fields},
            "sanitized_examples": {
                label: values for label, values in sorted(examples[slug].items())
            },
        }
        for slug, counter in sorted(results.items())
    }


def read_materialized_matches(
    db: ReadOnlyDatabase,
    resolver: TargetResolver,
    selected_servers: set[str],
) -> list[dict[str, object]]:
    rows = db.rows(
        """
        SELECT id, target_key, external_server_id, match_key, map_name, map_pretty_name,
               game_mode, started_server_time, ended_server_time, started_at, ended_at,
               allied_score, axis_score, winner, confidence_mode, source_basis,
               created_at, updated_at
        FROM rcon_materialized_matches
        ORDER BY target_key, match_key
        """
    )
    selected: list[dict[str, object]] = []
    for row in rows:
        slug = resolver.resolve(row.get("target_key"), row.get("external_server_id"))
        if slug not in selected_servers:
            continue
        row["server"] = slug
        row["bounds"] = bound_class(row)
        selected.append(row)
    return selected


def read_stat_aggregates(db: ReadOnlyDatabase) -> dict[tuple[str, str], dict[str, int]]:
    aggregates: dict[tuple[str, str], dict[str, int]] = {}
    for row in db.iterate(
        """
        SELECT target_key, match_key, COUNT(*) AS player_count,
               COALESCE(SUM(kills), 0) AS sum_kills,
               COALESCE(SUM(deaths), 0) AS sum_deaths,
               COALESCE(SUM(teamkills), 0) AS sum_teamkills,
               COALESCE(MAX(kills), 0) AS max_player_kills,
               COALESCE(MAX(deaths), 0) AS max_player_deaths
        FROM rcon_match_player_stats
        GROUP BY target_key, match_key
        ORDER BY target_key, match_key
        """
    ):
        key = (str(row.get("target_key") or ""), str(row.get("match_key") or ""))
        aggregates[key] = {
            field: as_int(row.get(field))
            for field in (
                "player_count",
                "sum_kills",
                "sum_deaths",
                "sum_teamkills",
                "max_player_kills",
                "max_player_deaths",
            )
        }
    return aggregates


def interval_overlap(
    first_lower: int | None,
    first_upper: int | None,
    second_lower: int | None,
    second_upper: int | None,
) -> bool:
    lower = max(
        float("-inf") if first_lower is None else first_lower,
        float("-inf") if second_lower is None else second_lower,
    )
    upper = min(
        float("inf") if first_upper is None else first_upper,
        float("inf") if second_upper is None else second_upper,
    )
    return lower <= upper


def scan_target_events(
    db: ReadOnlyDatabase,
    target_key: str,
    matches: list[dict[str, object]],
) -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    bounded = [match for match in matches if match.get("started_server_time") is not None or match.get("ended_server_time") is not None]
    lower_points = sorted({as_int(match["started_server_time"]) for match in bounded if match.get("started_server_time") is not None})
    upper_points = sorted({as_int(match["ended_server_time"]) for match in bounded if match.get("ended_server_time") is not None})
    before: dict[int, tuple[int, int]] = {}
    first_after: dict[int, tuple[int, int] | None] = {}
    through: dict[int, tuple[int, int]] = {}
    last_through: dict[int, tuple[int, int] | None] = {}
    lower_index = 0
    upper_index = 0
    total_events = 0
    total_kills = 0
    first_event: tuple[int, int] | None = None
    last_event: tuple[int, int] | None = None

    ranges = sorted(
        [
            (
                float("-inf") if match.get("started_server_time") is None else as_int(match.get("started_server_time")),
                float("inf") if match.get("ended_server_time") is None else as_int(match.get("ended_server_time")),
                index,
            )
            for index, match in enumerate(bounded)
        ],
        key=lambda item: (item[0], item[1], item[2]),
    )
    range_index = 0
    active: set[int] = set()
    end_heap: list[tuple[float, int]] = []
    assignment = Counter()
    max_multiplicity = 0
    max_example: dict[str, object] | None = None

    query = (
        "SELECT id, server_time, event_type FROM rcon_admin_log_events "
        "WHERE target_key = ? AND server_time IS NOT NULL "
        "AND event_type IN ('kill','team_switch','connected','disconnected','chat') "
        "ORDER BY server_time, id"
    )
    iterator = db.iterate(query, (target_key,))
    pending: dict[str, object] | None = next(iterator, None)
    while pending is not None:
        current_time = as_int(pending.get("server_time"))
        group_count = 0
        group_kills = 0
        group_first_id: int | None = None
        group_last_id: int | None = None
        while pending is not None and as_int(pending.get("server_time")) == current_time:
            event_id = as_int(pending.get("id"))
            group_first_id = event_id if group_first_id is None else group_first_id
            group_last_id = event_id
            group_count += 1
            group_kills += int(pending.get("event_type") == "kill")
            pending = next(iterator, None)

        while lower_index < len(lower_points) and lower_points[lower_index] <= current_time:
            point = lower_points[lower_index]
            before[point] = (total_events, total_kills)
            first_after[point] = (group_first_id or 0, current_time)
            lower_index += 1
        while upper_index < len(upper_points) and upper_points[upper_index] < current_time:
            point = upper_points[upper_index]
            through[point] = (total_events, total_kills)
            last_through[point] = last_event
            upper_index += 1

        while range_index < len(ranges) and ranges[range_index][0] <= current_time:
            _, upper, index = ranges[range_index]
            active.add(index)
            if upper != float("inf"):
                heapq.heappush(end_heap, (upper, index))
            range_index += 1
        while end_heap and end_heap[0][0] < current_time:
            _, index = heapq.heappop(end_heap)
            active.discard(index)
        multiplicity = len(active)
        if multiplicity == 0:
            assignment["eligible_assigned_0"] += group_count
            assignment["kill_assigned_0"] += group_kills
        elif multiplicity == 1:
            assignment["eligible_assigned_1"] += group_count
        else:
            assignment["eligible_assigned_many"] += group_count
            assignment["kill_assigned_many"] += group_kills
        if multiplicity > max_multiplicity:
            max_multiplicity = multiplicity
            max_example = {
                "event_ref": safe_ref("event", group_first_id),
                "server_time": current_time,
                "match_refs": sorted(
                    safe_ref("match", bounded[index].get("match_key")) for index in active
                ),
            }

        total_events += group_count
        total_kills += group_kills
        if first_event is None:
            first_event = (group_first_id or 0, current_time)
        last_event = (group_last_id or 0, current_time)
        while upper_index < len(upper_points) and upper_points[upper_index] == current_time:
            point = upper_points[upper_index]
            through[point] = (total_events, total_kills)
            last_through[point] = last_event
            upper_index += 1

    while lower_index < len(lower_points):
        point = lower_points[lower_index]
        before[point] = (total_events, total_kills)
        first_after[point] = None
        lower_index += 1
    while upper_index < len(upper_points):
        point = upper_points[upper_index]
        through[point] = (total_events, total_kills)
        last_through[point] = last_event
        upper_index += 1

    metrics: dict[str, dict[str, object]] = {}
    for match in bounded:
        lower = match.get("started_server_time")
        upper = match.get("ended_server_time")
        lower_counts = (0, 0) if lower is None else before[as_int(lower)]
        upper_counts = (total_events, total_kills) if upper is None else through[as_int(upper)]
        first_selected = first_event if lower is None else first_after[as_int(lower)]
        last_selected = last_event if upper is None else last_through[as_int(upper)]
        metrics[str(match.get("match_key") or "")] = {
            "selected_events": max(0, upper_counts[0] - lower_counts[0]),
            "selected_kills": max(0, upper_counts[1] - lower_counts[1]),
            "first_event_id": first_selected[0] if first_selected else None,
            "first_server_time": first_selected[1] if first_selected else None,
            "last_event_id": last_selected[0] if last_selected else None,
            "last_server_time": last_selected[1] if last_selected else None,
        }
    assignment["maximum_multiplicity"] = max_multiplicity
    assignment_result: dict[str, object] = dict(assignment)
    assignment_result["max_example"] = max_example
    assignment_result["eligible_events_streamed"] = total_events
    assignment_result["kill_events_streamed"] = total_kills
    return metrics, assignment_result


def summarize_materialized(
    matches: list[dict[str, object]],
    derived: list[dict[str, object]],
    boundaries: list[dict[str, object]],
    db: ReadOnlyDatabase,
    resolver: TargetResolver,
    selected_servers: set[str],
) -> tuple[
    dict[str, dict[str, object]],
    dict[tuple[str, str], dict[str, object]],
    dict[str, dict[str, object]],
]:
    by_target: dict[str, list[dict[str, object]]] = defaultdict(list)
    for match in matches:
        by_target[str(match.get("target_key") or "")].append(match)
    metric_by_raw_key: dict[tuple[str, str], dict[str, object]] = {}
    overlap_by_server: dict[str, Counter[str]] = {slug: Counter() for slug in selected_servers}
    overlap_examples: dict[str, dict[str, object] | None] = {slug: None for slug in selected_servers}
    for target_key, target_matches in sorted(by_target.items()):
        slug = resolver.resolve(target_key, target_matches[0].get("external_server_id"))
        if slug not in selected_servers:
            continue
        metrics, assignment = scan_target_events(db, target_key, target_matches)
        for match_key, metric in metrics.items():
            metric_by_raw_key[(target_key, match_key)] = metric
        target_max = as_int(assignment.get("maximum_multiplicity"))
        if target_max > overlap_by_server[slug].get("maximum_multiplicity", 0):
            example = assignment.get("max_example")
            overlap_examples[slug] = example if isinstance(example, dict) else None
        overlap_by_server[slug]["maximum_multiplicity"] = max(
            overlap_by_server[slug].get("maximum_multiplicity", 0), target_max
        )
        for key, value in assignment.items():
            if key in {"max_example", "maximum_multiplicity"}:
                continue
            overlap_by_server[slug][key] += as_int(value)

    boundary_times: dict[str, list[int]] = defaultdict(list)
    for row in boundaries:
        if row.get("server_time") is not None:
            boundary_times[str(row.get("target_key") or "")].append(as_int(row.get("server_time")))
    for values in boundary_times.values():
        values.sort()
    derived_both_by_target: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in derived:
        if bound_class(row) == "both_bounds":
            derived_both_by_target[str(row.get("target_key") or "")].append(row)

    materialized_summary: dict[str, dict[str, object]] = {}
    for slug in sorted(selected_servers):
        server_matches = [match for match in matches if match.get("server") == slug]
        bounds = Counter(str(match.get("bounds")) for match in server_matches)
        source_counts = Counter(str(match.get("source_basis") or "unknown") for match in server_matches)
        ended_rows = [match for match in server_matches if match.get("source_basis") == MATERIALIZED_SOURCE_END]
        started_times = [
            parsed
            for match in server_matches
            if (parsed := parse_timestamp(match.get("started_at"))) is not None
        ]
        ended_times = [
            parsed
            for match in server_matches
            if (parsed := parse_timestamp(match.get("ended_at"))) is not None
        ]
        lower_bounds = [
            as_int(match.get("started_server_time"))
            for match in server_matches
            if match.get("started_server_time") is not None
        ]
        upper_bounds = [
            as_int(match.get("ended_server_time"))
            for match in server_matches
            if match.get("ended_server_time") is not None
        ]
        materialized_summary[slug] = {
            "total": len(server_matches),
            "bounds": dict(bounds),
            "source_basis": dict(sorted(source_counts.items())),
            "session_fallback_total": sum(
                source in {"rcon-session", "rcon-session-window"} for source in [str(match.get("source_basis") or "") for match in server_matches]
            ),
            "admin_log_match_ended_total": len(ended_rows),
            "admin_log_match_ended_both_bounds": sum(bound_class(match) == "both_bounds" for match in ended_rows),
            "admin_log_match_ended_orphan_upper_only": sum(bound_class(match) == "upper_only" for match in ended_rows),
            "coverage": {
                "started_at": [
                    min(started_times).isoformat().replace("+00:00", "Z") if started_times else None,
                    max(started_times).isoformat().replace("+00:00", "Z") if started_times else None,
                ],
                "ended_at": [
                    min(ended_times).isoformat().replace("+00:00", "Z") if ended_times else None,
                    max(ended_times).isoformat().replace("+00:00", "Z") if ended_times else None,
                ],
                "started_server_time": [min(lower_bounds, default=None), max(lower_bounds, default=None)],
                "ended_server_time": [min(upper_bounds, default=None), max(upper_bounds, default=None)],
            },
        }

    detail_metrics: dict[str, dict[str, object]] = {}
    for match in matches:
        target_key = str(match.get("target_key") or "")
        match_key = str(match.get("match_key") or "")
        metric = dict(metric_by_raw_key.get((target_key, match_key), {}))
        lower = match.get("started_server_time")
        upper = match.get("ended_server_time")
        if lower is None and upper is None:
            metric["boundaries_crossed"] = 0
            metric["derived_complete_matches_crossed"] = 0
        else:
            times = boundary_times.get(target_key, [])
            left = 0 if lower is None else bisect.bisect_left(times, as_int(lower))
            right = len(times) if upper is None else bisect.bisect_right(times, as_int(upper))
            metric["boundaries_crossed"] = max(0, right - left)
            metric["derived_complete_matches_crossed"] = sum(
                interval_overlap(
                    None if lower is None else as_int(lower),
                    None if upper is None else as_int(upper),
                    as_int(candidate.get("started_server_time")),
                    as_int(candidate.get("ended_server_time")),
                )
                for candidate in derived_both_by_target.get(target_key, [])
            )
        detail_metrics[safe_ref("match", match_key)] = metric

    overlap_result: dict[str, dict[str, object]] = {}
    for slug in sorted(selected_servers):
        values: dict[str, object] = dict(overlap_by_server[slug])
        example = overlap_examples[slug]
        values["max_example"] = (
            {
                "event_ref": example.get("event_ref"),
                "server_time": example.get("server_time"),
                "match_refs": example.get("match_refs", []),
            }
            if isinstance(example, dict)
            else None
        )
        overlap_result[slug] = values
    return materialized_summary, metric_by_raw_key, overlap_result


def duration_seconds(match: Mapping[str, object]) -> int | None:
    lower = match.get("started_server_time")
    upper = match.get("ended_server_time")
    if lower is not None and upper is not None:
        return as_int(upper) - as_int(lower)
    start = parse_timestamp(match.get("started_at"))
    end = parse_timestamp(match.get("ended_at"))
    if start and end:
        return int((end - start).total_seconds())
    return None


def wall_timestamp_duration_seconds(match: Mapping[str, object]) -> int | None:
    start = parse_timestamp(match.get("started_at"))
    end = parse_timestamp(match.get("ended_at"))
    return int((end - start).total_seconds()) if start and end else None


def public_match_row(
    match: Mapping[str, object],
    metric: Mapping[str, object],
    stats: Mapping[str, int],
    *,
    anomaly_score: float | None = None,
) -> dict[str, object]:
    raw_key = str(match.get("match_key") or "")
    duration = duration_seconds(match)
    selected_kills = as_int(metric.get("selected_kills"))
    maximum_player_kills = stats.get("max_player_kills", 0)
    result: dict[str, object] = {
        "server": match.get("server"),
        "match_ref": safe_ref("match", raw_key),
        "map": match.get("map_pretty_name") or match.get("map_name"),
        "source_basis": match.get("source_basis"),
        "confidence_mode": match.get("confidence_mode"),
        "started_at": iso_timestamp(match.get("started_at")),
        "ended_at": iso_timestamp(match.get("ended_at")),
        "started_server_time": match.get("started_server_time"),
        "ended_server_time": match.get("ended_server_time"),
        "bounds": match.get("bounds") or bound_class(match),
        "duration_seconds": duration,
        "wall_timestamp_duration_seconds": wall_timestamp_duration_seconds(match),
        "whole_match_kpm": round(selected_kills / (duration / 60), 3) if duration and duration > 0 else None,
        "max_player_kpm": round(maximum_player_kills / (duration / 60), 3) if duration and duration > 0 else None,
        "max_player_kills": maximum_player_kills,
        "max_player_deaths": stats.get("max_player_deaths", 0),
        "total_player_kills": stats.get("sum_kills", 0),
        "total_player_deaths": stats.get("sum_deaths", 0),
        "total_teamkills": stats.get("sum_teamkills", 0),
        "player_count": stats.get("player_count", 0),
        "selected_kill_events": selected_kills,
        "selected_events": metric.get("selected_events", 0),
        "boundaries_crossed": metric.get("boundaries_crossed", 0),
        "derived_complete_matches_crossed": metric.get("derived_complete_matches_crossed", 0),
        "first_selected_event_ref": (
            safe_ref("event", metric.get("first_event_id"))
            if metric.get("first_event_id") is not None
            else None
        ),
        "first_selected_server_time": metric.get("first_server_time"),
        "last_selected_event_ref": (
            safe_ref("event", metric.get("last_event_id"))
            if metric.get("last_event_id") is not None
            else None
        ),
        "last_selected_server_time": metric.get("last_server_time"),
    }
    if anomaly_score is not None:
        result["duration_anomaly_mad_score"] = round(anomaly_score, 3)
    return result


def audit_stats_and_toplists(
    matches: list[dict[str, object]],
    metrics: dict[tuple[str, str], dict[str, object]],
    stats: dict[tuple[str, str], dict[str, int]],
    boundaries: list[dict[str, object]],
    derived: list[dict[str, object]],
) -> tuple[
    dict[str, object],
    dict[str, list[dict[str, object]]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
]:
    boundary_times: dict[str, list[int]] = defaultdict(list)
    for row in boundaries:
        if row.get("server_time") is not None:
            boundary_times[str(row.get("target_key") or "")].append(as_int(row.get("server_time")))
    for values in boundary_times.values():
        values.sort()
    derived_both: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in derived:
        if bound_class(row) == "both_bounds":
            derived_both[str(row.get("target_key") or "")].append(row)

    invariant_by_server: dict[str, Counter[str]] = defaultdict(Counter)
    violation_rows: list[dict[str, object]] = []
    public_rows: list[dict[str, object]] = []
    confirmed_inflated: list[dict[str, object]] = []
    for match in matches:
        target_key = str(match.get("target_key") or "")
        match_key = str(match.get("match_key") or "")
        metric = dict(metrics.get((target_key, match_key), {}))
        lower = match.get("started_server_time")
        upper = match.get("ended_server_time")
        if lower is None and upper is None:
            metric["boundaries_crossed"] = 0
            metric["derived_complete_matches_crossed"] = 0
        else:
            times = boundary_times.get(target_key, [])
            left = 0 if lower is None else bisect.bisect_left(times, as_int(lower))
            right = len(times) if upper is None else bisect.bisect_right(times, as_int(upper))
            metric["boundaries_crossed"] = max(0, right - left)
            metric["derived_complete_matches_crossed"] = sum(
                interval_overlap(
                    None if lower is None else as_int(lower),
                    None if upper is None else as_int(upper),
                    as_int(candidate.get("started_server_time")),
                    as_int(candidate.get("ended_server_time")),
                )
                for candidate in derived_both.get(target_key, [])
            )
        stat = stats.get((target_key, match_key), {})
        row = public_match_row(match, metric, stat)
        public_rows.append(row)
        slug = str(match.get("server") or "unmapped")
        if bound_class(match) == "both_bounds":
            invariant_by_server[slug]["matches_checked"] += 1
            event_kills = as_int(metric.get("selected_kills"))
            kills_ok = as_int(stat.get("sum_kills")) + as_int(stat.get("sum_teamkills")) == event_kills
            deaths_ok = as_int(stat.get("sum_deaths")) == event_kills
            invariant_by_server[slug]["kills_teamkills_ok" if kills_ok else "kills_teamkills_violation"] += 1
            invariant_by_server[slug]["deaths_ok" if deaths_ok else "deaths_violation"] += 1
            if not kills_ok or not deaths_ok:
                violation_rows.append(row)
        elif bound_class(match) in {"lower_only", "upper_only"}:
            if as_int(metric.get("derived_complete_matches_crossed")) >= 2 and as_int(stat.get("max_player_kills")) > 0:
                row = {**row, "confirmation_rule": "partial range spans at least two derived complete matches"}
                confirmed_inflated.append(row)

    valid_duration_rows = [
        row for row in public_rows if row.get("bounds") == "both_bounds" and as_int(row.get("duration_seconds"), -1) > 0
    ]
    duration_scores: dict[str, float] = {}
    for slug in sorted({str(row.get("server")) for row in valid_duration_rows}):
        server_rows = [row for row in valid_duration_rows if row.get("server") == slug]
        durations = [as_int(row.get("duration_seconds")) for row in server_rows]
        if not durations:
            continue
        median = statistics.median(durations)
        mad = statistics.median(abs(value - median) for value in durations) or 1
        for row in server_rows:
            duration_scores[str(row.get("match_ref"))] = abs(as_int(row.get("duration_seconds")) - median) / mad

    top_max = sorted(public_rows, key=lambda row: (-as_int(row.get("max_player_kills")), str(row.get("match_ref"))))[:20]
    top_total = sorted(public_rows, key=lambda row: (-as_int(row.get("total_player_kills")), str(row.get("match_ref"))))[:20]
    duration_ranked = sorted(
        valid_duration_rows,
        key=lambda row: (-duration_scores.get(str(row.get("match_ref")), 0.0), str(row.get("match_ref"))),
    )[:20]
    duration_ranked = [
        {**row, "duration_anomaly_mad_score": round(duration_scores.get(str(row.get("match_ref")), 0.0), 3)}
        for row in duration_ranked
    ]
    invariants = {
        "by_server": {slug: dict(counter) for slug, counter in sorted(invariant_by_server.items())},
        "violations": violation_rows,
        "note": "Internal consistency does not prove source completeness; unknown TEAM KILL candidates are outside K.",
    }
    top = {
        "by_max_player_kills": top_max,
        "by_total_player_kills": top_total,
        "by_duration_anomaly": duration_ranked,
    }
    confirmed_refs = {str(row.get("match_ref")) for row in confirmed_inflated}
    partial_rows = [
        {
            **row,
            "inflation_classification": (
                "confirmed" if str(row.get("match_ref")) in confirmed_refs else "not-confirmed"
            ),
        }
        for row in public_rows
        if row.get("bounds") in {"lower_only", "upper_only"}
    ]
    partial_rows.sort(key=lambda row: (str(row.get("server")), str(row.get("match_ref"))))
    public_rows.sort(key=lambda row: (str(row.get("server")), str(row.get("match_ref"))))
    return invariants, top, confirmed_inflated, partial_rows, public_rows


def normalize_window_map(row: Mapping[str, object]) -> str | None:
    return normalize_map_name(row.get("map_pretty_name") or row.get("map_name"))


def cutoff_tie_membership(
    rows: Sequence[Mapping[str, object]], limit: int = 100
) -> tuple[int, int, bool]:
    """Return cutoff-key counts inside/outside the limit and whether they straddle it."""
    if limit <= 0 or len(rows) <= limit:
        return 0, 0, False
    cutoff_key = (rows[limit - 1].get("last_seen_at"), rows[limit - 1].get("display_name"))
    inside = sum(
        (row.get("last_seen_at"), row.get("display_name")) == cutoff_key
        for row in rows[:limit]
    )
    outside = sum(
        (row.get("last_seen_at"), row.get("display_name")) == cutoff_key
        for row in rows[limit:]
    )
    return inside, outside, inside > 0 and outside > 0


def audit_windows_and_stale(
    db: ReadOnlyDatabase,
    resolver: TargetResolver,
    selected_servers: set[str],
    persisted: list[dict[str, object]],
    derived: list[dict[str, object]],
    range_metrics: dict[tuple[str, str], dict[str, object]],
) -> tuple[dict[str, object], dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
    rows = db.rows(
        """
        SELECT w.id, w.target_id, t.target_key, t.external_server_id, t.display_name,
               w.session_key, w.map_name, w.map_pretty_name, w.first_seen_at,
               w.last_seen_at, w.sample_count, w.status, w.confidence_mode
        FROM rcon_historical_competitive_windows AS w
        JOIN rcon_historical_targets AS t ON t.id = w.target_id
        ORDER BY w.last_seen_at DESC, t.display_name ASC, w.id ASC
        """
    )
    for row in rows:
        row["server"] = resolver.resolve(row.get("target_key"), row.get("external_server_id"))
        row["normalized_map"] = normalize_window_map(row)
    top100 = rows[:100]
    cutoff_tie_inside, cutoff_tie_outside, cutoff_tie = cutoff_tie_membership(rows)
    cutoff_tie_count = cutoff_tie_inside + cutoff_tie_outside

    existing: set[tuple[str, str | None]] = set()
    for match in persisted:
        if match.get("source_basis") == MATERIALIZED_SOURCE_END:
            existing.add(
                (
                    str(match.get("target_key") or ""),
                    normalize_map_name(match.get("map_pretty_name") or match.get("map_name")),
                )
            )
    for match in derived:
        if match.get("source_basis") == MATERIALIZED_SOURCE_END:
            existing.add(
                (
                    str(match.get("target_key") or ""),
                    normalize_map_name(match.get("map_name")),
                )
            )

    suppressed_top: list[dict[str, object]] = []
    suppressed_all: list[dict[str, object]] = []
    derived_fallback: list[dict[str, object]] = []
    derived_exact_by_map: dict[tuple[str, str | None], list[dict[str, object]]] = defaultdict(list)
    for match in derived:
        if bound_class(match) == "both_bounds":
            derived_exact_by_map[
                (
                    str(match.get("target_key") or ""),
                    normalize_map_name(match.get("map_name")),
                )
            ].append(match)
    suppression_relations: dict[str, Counter[str]] = {
        slug: Counter() for slug in selected_servers
    }
    for index, row in enumerate(rows):
        key = (str(row.get("target_key") or ""), row.get("normalized_map"))
        suppressed = key in existing
        if suppressed:
            suppressed_all.append(row)
            if index < 100:
                suppressed_top.append(row)
            slug = row.get("server")
            if slug in selected_servers:
                window_start = parse_timestamp(row.get("first_seen_at"))
                window_end = parse_timestamp(row.get("last_seen_at"))
                relation = "unresolved_temporal_relation"
                exacts = derived_exact_by_map.get(key, [])
                if window_start and window_end and exacts:
                    nearest_edge: float | None = None
                    overlaps = False
                    for match in exacts:
                        exact_start, exact_end = match_time_bounds(match)
                        if not exact_start or not exact_end:
                            continue
                        overlaps = overlaps or min(window_end, exact_end) >= max(window_start, exact_start)
                        edge = min(
                            abs((window_start - exact_start).total_seconds()),
                            abs((window_start - exact_end).total_seconds()),
                            abs((window_end - exact_start).total_seconds()),
                            abs((window_end - exact_end).total_seconds()),
                        )
                        nearest_edge = edge if nearest_edge is None else min(nearest_edge, edge)
                    if overlaps:
                        relation = "temporally_overlaps_exact_match"
                    elif nearest_edge is not None and nearest_edge <= 3600:
                        relation = "within_one_hour_of_exact_match"
                    elif nearest_edge is not None:
                        relation = "temporally_distant_map_only_candidate"
                suppression_relations[str(slug)][relation] += 1
        elif index < 100:
            derived_fallback.append(
                {
                    "target_key": row.get("target_key"),
                    "external_server_id": row.get("external_server_id"),
                    "match_key": f"session:{row.get('session_key')}",
                    "map_name": row.get("map_name"),
                    "map_pretty_name": row.get("map_pretty_name"),
                    "started_server_time": None,
                    "ended_server_time": None,
                    "started_at": row.get("first_seen_at"),
                    "ended_at": row.get("last_seen_at"),
                    "confidence_mode": "session-fallback",
                    "source_basis": "rcon-session",
                }
            )

    fallback_summary: dict[str, object] = {
        "global_window_count": len(rows),
        "global_top100_size": len(top100),
        "global_top100_distribution": {},
        "cutoff_tie_candidate_count": cutoff_tie_count,
        "cutoff_tie_inside_top100": cutoff_tie_inside,
        "cutoff_tie_outside_top100": cutoff_tie_outside,
        "production_membership_ambiguous_at_cutoff": cutoff_tie,
        "by_server": {},
    }
    distribution = Counter(
        str(row.get("server")) if row.get("server") in selected_servers else "other"
        for row in top100
    )
    fallback_summary["global_top100_distribution"] = dict(sorted(distribution.items()))
    for slug in sorted(selected_servers):
        server_rows = [row for row in rows if row.get("server") == slug]
        server_top = [row for row in top100 if row.get("server") == slug]
        repeated_groups = Counter(str(row.get("normalized_map") or "") for row in server_rows)
        fallback_summary["by_server"][slug] = {
            "all_windows": len(server_rows),
            "inside_global_newest_100": len(server_top),
            "outside_global_newest_100": len(server_rows) - len(server_top),
            "suppressed_by_map_only_inside_top100": sum(row.get("server") == slug for row in suppressed_top),
            "suppressed_by_map_only_all_windows": sum(row.get("server") == slug for row in suppressed_all),
            "suppression_temporal_classification": dict(suppression_relations[slug]),
            "repeated_normalized_map_groups": sum(count > 1 for count in repeated_groups.values()),
            "windows_in_repeated_map_groups": sum(count for count in repeated_groups.values() if count > 1),
            "coverage": {
                "first_seen_at": min(
                    (iso_timestamp(row.get("first_seen_at")) for row in server_rows if iso_timestamp(row.get("first_seen_at"))),
                    default=None,
                ),
                "last_seen_at": max(
                    (iso_timestamp(row.get("last_seen_at")) for row in server_rows if iso_timestamp(row.get("last_seen_at"))),
                    default=None,
                ),
            },
        }

    derived_admin_keys = {str(match.get("match_key") or "") for match in derived}
    derived_fallback_keys = {str(match.get("match_key") or "") for match in derived_fallback}
    derived_now = derived_admin_keys | derived_fallback_keys
    persisted_keys = {str(match.get("match_key") or "") for match in persisted}
    stale_rows = [match for match in persisted if str(match.get("match_key") or "") not in derived_now]
    stale_summary: dict[str, object] = {"by_server": {}, "not_currently_derivable": []}
    derived_complete_by_target: dict[str, list[dict[str, object]]] = defaultdict(list)
    for match in derived:
        if bound_class(match) == "both_bounds":
            derived_complete_by_target[str(match.get("target_key") or "")].append(match)
    for slug in sorted(selected_servers):
        server_stale = [match for match in stale_rows if match.get("server") == slug]
        classes = Counter()
        stale_shared_event_rows = 0
        stale_selected_kills = 0
        fallback_temporal_duplicates = 0
        for match in server_stale:
            source = str(match.get("source_basis") or "")
            bounds = bound_class(match)
            if source == "admin-log-match-start":
                label = "stale_start_only"
            elif source == MATERIALIZED_SOURCE_END and bounds == "upper_only":
                label = "stale_end_only"
            elif source == "rcon-session-window" or str(match.get("match_key") or "").startswith("session:"):
                label = "not_currently_derivable_fallback"
            else:
                label = "other_stale"
            classes[label] += 1
            target_key = str(match.get("target_key") or "")
            match_key = str(match.get("match_key") or "")
            metric = range_metrics.get((target_key, match_key), {})
            selected_kills = as_int(metric.get("selected_kills"))
            complete_overlap_count = 0
            if bounds != "no_bounds":
                complete_overlap_count = sum(
                    interval_overlap(
                        None if match.get("started_server_time") is None else as_int(match.get("started_server_time")),
                        None if match.get("ended_server_time") is None else as_int(match.get("ended_server_time")),
                        as_int(candidate.get("started_server_time")),
                        as_int(candidate.get("ended_server_time")),
                    )
                    for candidate in derived_complete_by_target.get(target_key, [])
                )
                if complete_overlap_count and selected_kills:
                    stale_shared_event_rows += 1
                    stale_selected_kills += selected_kills
            else:
                stale_start = parse_timestamp(match.get("started_at"))
                stale_end = parse_timestamp(match.get("ended_at"))
                stale_map = normalize_map_name(match.get("map_pretty_name") or match.get("map_name"))
                if stale_start and stale_end:
                    fallback_temporal_duplicates += int(
                        any(
                            normalize_map_name(candidate.get("map_name")) == stale_map
                            and (candidate_start := match_time_bounds(candidate)[0]) is not None
                            and (candidate_end := match_time_bounds(candidate)[1]) is not None
                            and min(stale_end, candidate_end) >= max(stale_start, candidate_start)
                            for candidate in derived_complete_by_target.get(target_key, [])
                        )
                    )
            stale_summary["not_currently_derivable"].append(
                {
                    "server": slug,
                    "match_ref": safe_ref("match", match.get("match_key")),
                    "classification": label,
                    "bounds": bounds,
                    "source_basis": source,
                    "selected_kills_under_current_semantics": selected_kills,
                    "derived_complete_ranges_overlapped": complete_overlap_count,
                }
            )
        stale_summary["by_server"][slug] = {
            "persisted": sum(match.get("server") == slug for match in persisted),
            "currently_derivable": sum(
                match.get("server") == slug and str(match.get("match_key") or "") in derived_now
                for match in persisted
            ),
            "not_currently_derivable": len(server_stale),
            "classifications": dict(classes),
            "stale_bounded_rows_sharing_kills_with_complete_ranges": stale_shared_event_rows,
            "sum_selected_kills_across_those_stale_rows": stale_selected_kills,
            "stale_fallbacks_temporally_overlapping_exact_match": fallback_temporal_duplicates,
            "derived_now_missing_from_persisted": sum(
                resolver.resolve(match.get("target_key"), match.get("external_server_id")) == slug
                and str(match.get("match_key") or "") not in persisted_keys
                for match in [*derived, *derived_fallback]
            ),
        }
    stale_summary["not_currently_derivable"].sort(
        key=lambda row: (str(row.get("server")), str(row.get("match_ref")))
    )
    return fallback_summary, stale_summary, rows, derived_fallback


def extract_mode_and_score(payload: Mapping[str, object]) -> tuple[str | None, tuple[int, int] | None]:
    mode = payload.get("game_mode") or payload.get("mode")
    allied = payload.get("allied_score")
    axis = payload.get("axis_score")
    score = None
    if allied is not None and axis is not None:
        score = (as_int(allied), as_int(axis))
    return (str(mode) if mode is not None else None, score)


def audit_competitive_merging(
    db: ReadOnlyDatabase,
    resolver: TargetResolver,
    selected_servers: set[str],
    windows: list[dict[str, object]],
    boundaries: list[dict[str, object]],
) -> dict[str, object]:
    results: dict[str, Counter[str]] = {slug: Counter() for slug in selected_servers}
    window_evidence: dict[int, set[str]] = defaultdict(set)
    windows_by_target: dict[int, list[dict[str, object]]] = defaultdict(list)
    for window in windows:
        if window.get("server") in selected_servers:
            windows_by_target[as_int(window.get("target_id"))].append(window)
    for target_windows in windows_by_target.values():
        target_windows.sort(key=lambda row: (parse_timestamp(row.get("first_seen_at")) or datetime.min.replace(tzinfo=timezone.utc), as_int(row.get("id"))))

    for target_id, target_windows in sorted(windows_by_target.items()):
        slug = resolver.target_id_to_slug.get(target_id)
        if slug not in selected_servers:
            continue
        previous: dict[str, object] | None = None
        window_starts = [
            parse_timestamp(window.get("first_seen_at"))
            or datetime.min.replace(tzinfo=timezone.utc)
            for window in target_windows
        ]
        query = (
            "SELECT id, captured_at, current_map, normalized_payload_json "
            "FROM rcon_historical_samples WHERE target_id = ? ORDER BY id"
        )
        for row in db.iterate(query, (target_id,)):
            captured = parse_timestamp(row.get("captured_at"))
            if captured is None:
                results[slug]["unparseable_sample_timestamps"] += 1
                continue
            window_index = bisect.bisect_right(window_starts, captured) - 1
            current_window = target_windows[window_index] if window_index >= 0 else None
            if current_window:
                start = parse_timestamp(current_window.get("first_seen_at"))
                end = parse_timestamp(current_window.get("last_seen_at"))
                if not (start and end and start <= captured <= end):
                    current_window = None
            if previous is not None:
                previous_time = parse_timestamp(previous.get("captured_at"))
                if previous_time:
                    delta = int((captured - previous_time).total_seconds())
                    same_normalized = normalize_map_name(row.get("current_map")) == normalize_map_name(previous.get("current_map"))
                    if same_normalized and delta <= 1800:
                        results[slug]["same_normalized_map_pairs_gap_le_1800"] += 1
                        if delta < 0:
                            results[slug]["negative_gap_pairs"] += 1
                        if str(row.get("current_map") or "") != str(previous.get("current_map") or ""):
                            results[slug]["raw_map_identity_changed"] += 1
                            if current_window:
                                window_evidence[as_int(current_window.get("id"))].add("raw-map-change")
                        current_payload = json_object(row.get("normalized_payload_json"))
                        previous_payload = json_object(previous.get("normalized_payload_json"))
                        current_mode, current_score = extract_mode_and_score(current_payload)
                        previous_mode, previous_score = extract_mode_and_score(previous_payload)
                        if current_mode and previous_mode and current_mode != previous_mode:
                            results[slug]["mode_changed"] += 1
                            if current_window:
                                window_evidence[as_int(current_window.get("id"))].add("mode-change")
                        if current_score and previous_score and sum(current_score) < sum(previous_score):
                            results[slug]["score_reset_candidates"] += 1
                            if current_window:
                                window_evidence[as_int(current_window.get("id"))].add("score-reset")
            previous = row

    boundary_times_by_key: dict[str, list[tuple[datetime, int, str]]] = defaultdict(list)
    for row in boundaries:
        parsed = server_time_timestamp(row.get("server_time"))
        if parsed:
            boundary_times_by_key[str(row.get("target_key") or "")].append(
                (parsed, as_int(row.get("id")), str(row.get("event_type") or ""))
            )
            slug = resolver.resolve(row.get("target_key"), row.get("external_server_id"))
            if slug in selected_servers:
                results[str(slug)]["boundary_rows_timed_by_server_time"] += 1
        else:
            slug = resolver.resolve(row.get("target_key"), row.get("external_server_id"))
            if slug in selected_servers:
                results[str(slug)]["boundary_rows_without_plausible_unix_server_time"] += 1
    for window in windows:
        slug = window.get("server")
        if slug not in selected_servers:
            continue
        start = parse_timestamp(window.get("first_seen_at"))
        end = parse_timestamp(window.get("last_seen_at"))
        if start and end:
            duration = int((end - start).total_seconds())
            results[str(slug)]["windows_over_2h"] += int(duration > 7200)
            results[str(slug)]["maximum_window_duration_seconds"] = max(
                results[str(slug)].get("maximum_window_duration_seconds", 0), duration
            )
            contained_boundaries = [
                (value, event_id, event_type)
                for value, event_id, event_type in boundary_times_by_key.get(
                    str(window.get("target_key") or ""), []
                )
                if start <= value <= end
            ]
            boundary_count = len(contained_boundaries)
            if boundary_count:
                complete_pair_floor = count_ordered_boundary_pairs(contained_boundaries)
                contained_types = [event_type for _, _, event_type in contained_boundaries]
                results[str(slug)]["windows_containing_adminlog_boundary"] += 1
                results[str(slug)]["windows_containing_2plus_boundaries"] += int(boundary_count >= 2)
                results[str(slug)]["windows_containing_4plus_boundaries"] += int(boundary_count >= 4)
                results[str(slug)]["windows_containing_start_and_end"] += int(
                    "match_start" in contained_types and "match_end" in contained_types
                )
                results[str(slug)]["maximum_boundaries_in_one_window"] = max(
                    results[str(slug)].get("maximum_boundaries_in_one_window", 0),
                    boundary_count,
                )
                results[str(slug)]["maximum_complete_boundary_pairs_in_one_window"] = max(
                    results[str(slug)].get("maximum_complete_boundary_pairs_in_one_window", 0),
                    complete_pair_floor,
                )
                results[str(slug)]["minimum_extra_rounds_indicated_by_boundary_pairs"] += max(
                    0, complete_pair_floor - 1
                )
                window_evidence[as_int(window.get("id"))].add("adminlog-boundary")
    evidence_counts: dict[str, Counter[str]] = {slug: Counter() for slug in selected_servers}
    for window in windows:
        slug = window.get("server")
        if slug not in selected_servers:
            continue
        evidence = window_evidence.get(as_int(window.get("id")), set())
        for signature in evidence:
            evidence_counts[str(slug)][f"windows_with_{signature}"] += 1
        if len(evidence) >= 2:
            evidence_counts[str(slug)]["windows_with_multiple_merge_signals"] += 1
    audited_numeric_fields = (
        "same_normalized_map_pairs_gap_le_1800",
        "negative_gap_pairs",
        "raw_map_identity_changed",
        "mode_changed",
        "score_reset_candidates",
        "windows_over_2h",
        "windows_containing_adminlog_boundary",
        "windows_containing_2plus_boundaries",
        "windows_containing_4plus_boundaries",
        "windows_containing_start_and_end",
        "maximum_boundaries_in_one_window",
        "maximum_complete_boundary_pairs_in_one_window",
        "minimum_extra_rounds_indicated_by_boundary_pairs",
        "windows_with_adminlog-boundary",
        "windows_with_raw-map-change",
        "windows_with_mode-change",
        "windows_with_score-reset",
        "windows_with_multiple_merge_signals",
    )
    return {
        "by_server": {
            slug: {
                **{
                    field: ({**results[slug], **evidence_counts[slug]}).get(field, 0)
                    for field in audited_numeric_fields
                },
                "maximum_window_duration_seconds": results[slug].get(
                    "maximum_window_duration_seconds", 0
                ),
                "boundary_rows_timed_by_server_time": results[slug].get(
                    "boundary_rows_timed_by_server_time", 0
                ),
                "boundary_rows_without_plausible_unix_server_time": results[slug].get(
                    "boundary_rows_without_plausible_unix_server_time", 0
                ),
                "distinct_layer_identity_evidence": "unavailable-as-separate-source-field",
            }
            for slug in sorted(selected_servers)
        },
        "classification_note": "Signals are candidates, not automatic proof that every window represents multiple rounds.",
    }


def classify_parser_signature(raw: str, canonical: str) -> list[str]:
    signatures: set[str] = set()
    combined = canonical + "\n" + raw
    upper = combined.upper()
    if raw[:1].isspace():
        signatures.add("leading-whitespace")
    prefix = PREFIX_RE.match(raw)
    if prefix is None and raw.lstrip().startswith("["):
        signatures.add("prefix-not-recognized")
    if raw.startswith("[ ("):
        signatures.add("empty-relative-time")
    if MATCH_START_RELAXED_RE.search(combined):
        signatures.add("match-start-like")
        if "MATCH START" not in combined:
            signatures.add("case-or-spacing-variant")
        tail = re.split(r"MATCH\s+START", combined, flags=re.IGNORECASE)[-1].strip()
        if tail and not re.search(r"\s[A-Za-z]+$", tail):
            signatures.add("match-start-mode-suffix")
    if MATCH_END_RELAXED_RE.search(combined):
        signatures.add("match-end-like")
        if "`" not in combined:
            signatures.add("match-end-backtick-variant")
        if not ("ALLIED (" in upper and ") AXIS" in upper):
            signatures.add("match-end-score-layout-variant")
    if TEAM_KILL_RELAXED_RE.search(combined):
        signatures.add("explicit-team-kill")
    return sorted(signatures)


def audit_parser(
    db: ReadOnlyDatabase,
    resolver: TargetResolver,
    selected_servers: set[str],
    max_examples: int,
) -> dict[str, object]:
    query = """
        SELECT id, target_key, external_server_id, event_timestamp, server_time,
               raw_message, canonical_message
        FROM rcon_admin_log_events
        WHERE event_type = 'unknown'
          AND (
            UPPER(COALESCE(canonical_message, '')) LIKE '%MATCH%'
            OR UPPER(COALESCE(canonical_message, '')) LIKE '%START%'
            OR UPPER(COALESCE(canonical_message, '')) LIKE '%ENDED%'
            OR UPPER(COALESCE(canonical_message, '')) LIKE '%TEAM KILL%'
            OR UPPER(COALESCE(raw_message, '')) LIKE '%MATCH%'
            OR UPPER(COALESCE(raw_message, '')) LIKE '%START%'
            OR UPPER(COALESCE(raw_message, '')) LIKE '%ENDED%'
            OR UPPER(COALESCE(raw_message, '')) LIKE '%TEAM KILL%'
          )
        ORDER BY target_key, id
    """
    results: dict[str, Counter[str]] = {slug: Counter() for slug in selected_servers}
    examples: dict[str, list[dict[str, object]]] = {slug: [] for slug in selected_servers}
    for row in db.iterate(query):
        slug = resolver.resolve(row.get("target_key"), row.get("external_server_id"))
        if slug not in selected_servers:
            continue
        raw = str(row.get("raw_message") or "")
        canonical = str(row.get("canonical_message") or "")
        signatures = classify_parser_signature(raw, canonical)
        if not signatures:
            continue
        reparsed = parse_rcon_admin_log_entry(
            {"timestamp": row.get("event_timestamp"), "message": raw}
        )
        results[slug]["candidate_unknown_rows"] += 1
        reparsed_type = str(reparsed.get("event_type") or "unknown")
        results[slug]["reparsed_non_unknown"] += int(reparsed_type != "unknown")
        results[slug]["null_server_time_candidates"] += int(row.get("server_time") is None)
        for signature in signatures:
            results[slug][signature] += 1
        if len(examples[slug]) < max_examples:
            examples[slug].append(
                {
                    "event_id": row.get("id"),
                    "stored_type": "unknown",
                    "reparsed_type": reparsed_type,
                    "server_time_is_null": row.get("server_time") is None,
                    "signatures": signatures,
                }
            )
    return {
        "by_server": {
            slug: {"counts": dict(results[slug]), "sanitized_examples": examples[slug]}
            for slug in sorted(selected_servers)
        }
    }


def audit_dedupe(
    db: ReadOnlyDatabase,
    resolver: TargetResolver,
    selected_servers: set[str],
) -> dict[str, object]:
    aggregate_rows = db.rows(
        """
        SELECT target_key, MIN(external_server_id) AS external_server_id,
               COUNT(*) AS duplicate_identity_groups,
               COALESCE(SUM(row_count - 1), 0) AS duplicate_extra_rows,
               COALESCE(MAX(row_count), 0) AS maximum_group_size
        FROM (
            SELECT target_key, MIN(external_server_id) AS external_server_id,
                   server_time, canonical_message,
                   COUNT(*) AS row_count
            FROM rcon_admin_log_events
            GROUP BY target_key, server_time, canonical_message
            HAVING COUNT(*) > 1
        ) AS duplicate_groups
        GROUP BY target_key
        ORDER BY target_key
        """
    )
    null_rows = db.rows(
        """
        SELECT target_key, external_server_id,
               SUM(CASE WHEN server_time IS NULL THEN 1 ELSE 0 END) AS null_server_time
        FROM rcon_admin_log_events
        GROUP BY target_key, external_server_id
        ORDER BY target_key
        """
    )
    results: dict[str, Counter[str]] = {slug: Counter() for slug in selected_servers}
    for row in [*aggregate_rows, *null_rows]:
        slug = resolver.resolve(row.get("target_key"), row.get("external_server_id"))
        if slug not in selected_servers:
            continue
        for field in (
            "duplicate_identity_groups",
            "duplicate_extra_rows",
            "maximum_group_size",
            "null_server_time",
        ):
            if row.get(field) is not None:
                if field == "maximum_group_size":
                    results[slug][field] = max(results[slug].get(field, 0), as_int(row.get(field)))
                else:
                    results[slug][field] += as_int(row.get(field))

    for row in db.iterate(
        "SELECT id, target_key, external_server_id, raw_message, canonical_message "
        "FROM rcon_admin_log_events ORDER BY target_key, id"
    ):
        slug = resolver.resolve(row.get("target_key"), row.get("external_server_id"))
        if slug not in selected_servers:
            continue
        raw = str(row.get("raw_message") or "")
        stored = str(row.get("canonical_message") or "")
        current = canonicalize_admin_message(raw)
        if stored == current:
            results[slug]["canonical_matches_current"] += 1
        else:
            results[slug]["canonical_drift_rows"] += 1
            if stored == raw and current != stored:
                results[slug]["possible_legacy_raw_canonical"] += 1

    schema: dict[str, object]
    if db.dialect == "sqlite":
        indexes = db.rows("PRAGMA index_list(rcon_admin_log_events)")
        dedupe_indexes: list[dict[str, object]] = []
        for row in indexes:
            name = str(row.get("name") or "")
            if "dedupe" not in name.lower() or not re.fullmatch(r"[A-Za-z0-9_]+", name):
                continue
            columns = [
                str(info.get("name") or "")
                for info in db.rows(f'PRAGMA index_info("{name}")')
            ]
            dedupe_indexes.append(
                {"name": name, "unique": bool(row.get("unique")), "columns": columns}
            )
        expected_columns = ["target_key", "server_time", "canonical_message"]
        schema = {
            "backend": "sqlite",
            "dedupe_indexes": dedupe_indexes,
            "expected_identity_unique": any(
                bool(index.get("unique")) and index.get("columns") == expected_columns
                for index in dedupe_indexes
            ),
            "application_identity_predicate": "target_key = ? AND server_time IS ? AND canonical_message = ?",
            "application_null_server_time_equality": "IS treats NULL as equal",
            "nulls_not_distinct": False,
        }
    else:
        constraints = db.rows(
            """
            SELECT pg_get_constraintdef(c.oid) AS definition
            FROM pg_constraint AS c
            JOIN pg_class AS t ON t.oid = c.conrelid
            WHERE t.relname = 'rcon_admin_log_events'
              AND t.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = current_schema())
              AND c.contype = 'u'
            ORDER BY c.conname
            """
        )
        indexes = db.rows(
            """
            SELECT pg_get_indexdef(i.indexrelid) AS definition
            FROM pg_index AS i
            JOIN pg_class AS t ON t.oid = i.indrelid
            WHERE t.relname = 'rcon_admin_log_events'
              AND t.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = current_schema())
              AND i.indisunique
            ORDER BY i.indexrelid
            """
        )
        definitions = [str(row.get("definition") or "") for row in [*constraints, *indexes]]
        normalized_definitions = [re.sub(r'["\s]', "", value.upper()) for value in definitions]
        expected_signature = "(TARGET_KEY,SERVER_TIME,CANONICAL_MESSAGE)"
        schema = {
            "backend": "postgres",
            "unique_constraint_count": len(constraints),
            "unique_index_count": len(indexes),
            "expected_identity_unique": any(expected_signature in value for value in normalized_definitions),
            "nulls_not_distinct": any("NULLS NOT DISTINCT" in value.upper() for value in definitions),
        }
    count_fields = (
        "duplicate_identity_groups",
        "duplicate_extra_rows",
        "maximum_group_size",
        "null_server_time",
        "canonical_matches_current",
        "canonical_drift_rows",
        "possible_legacy_raw_canonical",
    )
    return {
        "effective_schema": schema,
        "by_server": {
            slug: {field: results[slug].get(field, 0) for field in count_fields}
            for slug in sorted(selected_servers)
        },
        "collision_loss_assessment": "UNRESOLVED: persisted rows do not contain individually rejected observations.",
        "different_poll_timestamps_are_not_proof": True,
    }


def summarize_gaps(values: list[datetime]) -> dict[str, object]:
    ordered = sorted(set(values))
    gap_rows = [
        (int((current - previous).total_seconds()), previous, current)
        for previous, current in zip(ordered, ordered[1:])
    ]
    gaps = [row[0] for row in gap_rows]
    maximum = max(gap_rows, default=None, key=lambda row: (row[0], row[1]))
    return {
        "distinct_observation_times": len(ordered),
        "first": ordered[0].isoformat().replace("+00:00", "Z") if ordered else None,
        "last": ordered[-1].isoformat().replace("+00:00", "Z") if ordered else None,
        "gaps_over_600s": sum(value > 600 for value in gaps),
        "gaps_over_900s": sum(value > 900 for value in gaps),
        "gaps_over_3600s": sum(value > 3600 for value in gaps),
        "maximum_gap_seconds": max(gaps, default=0),
        "maximum_gap_interval": (
            [
                maximum[1].isoformat().replace("+00:00", "Z"),
                maximum[2].isoformat().replace("+00:00", "Z"),
            ]
            if maximum
            else None
        ),
    }


def audit_acquisition(
    db: ReadOnlyDatabase,
    resolver: TargetResolver,
    selected_servers: set[str],
    split_at: datetime | None,
) -> dict[str, object]:
    created_by_server: dict[str, list[datetime]] = {slug: [] for slug in selected_servers}
    event_by_server: dict[str, list[datetime]] = {slug: [] for slug in selected_servers}
    era_counts: dict[str, Counter[str]] = {slug: Counter() for slug in selected_servers}
    query = """
        SELECT target_key, external_server_id, created_at, event_timestamp, COUNT(*) AS event_count
        FROM rcon_admin_log_events
        GROUP BY target_key, external_server_id, created_at, event_timestamp
        ORDER BY target_key, created_at, event_timestamp
    """
    for row in db.iterate(query):
        slug = resolver.resolve(row.get("target_key"), row.get("external_server_id"))
        if slug not in selected_servers:
            continue
        created = parse_timestamp(row.get("created_at"))
        event = parse_timestamp(row.get("event_timestamp"))
        if created:
            created_by_server[slug].append(created)
        else:
            era_counts[slug]["unparseable_created_at_groups"] += 1
        if event:
            event_by_server[slug].append(event)
        else:
            era_counts[slug]["unparseable_event_timestamp_groups"] += 1
        if split_at and created:
            era_counts[slug]["events_before_task271_split"] += as_int(row.get("event_count")) * int(created < split_at)
            era_counts[slug]["events_after_task271_split"] += as_int(row.get("event_count")) * int(created >= split_at)
    return {
        "task271_split_reference": split_at.isoformat().replace("+00:00", "Z") if split_at else None,
        "by_server": {
            slug: {
                "created_at_batches": summarize_gaps(created_by_server[slug]),
                "event_timestamps": summarize_gaps(event_by_server[slug]),
                "eras": dict(era_counts[slug]),
            }
            for slug in sorted(selected_servers)
        },
        "worker_ledger_available": False,
        "assessment_note": "Observed event gaps alone do not prove a failed poll or lost event.",
    }


def candidate_score(rcon: Mapping[str, object], scoreboard: Mapping[str, object]) -> int | None:
    if normalize_map_name(rcon.get("map_name")) != normalize_map_name(
        scoreboard.get("map_pretty_name") or scoreboard.get("map_name")
    ):
        return None
    rcon_start, rcon_end = match_time_bounds(rcon)
    board_start = parse_timestamp(scoreboard.get("started_at"))
    board_end = parse_timestamp(scoreboard.get("ended_at"))
    if not all((rcon_start, rcon_end, board_start, board_end)):
        return None
    assert rcon_start and rcon_end and board_start and board_end
    if rcon_end < rcon_start:
        rcon_start, rcon_end = rcon_end, rcon_start
    if board_end < board_start:
        board_start, board_end = board_end, board_start
    overlap = max(0, int((min(rcon_end, board_end) - max(rcon_start, board_start)).total_seconds()))
    score = 3 if overlap > 0 else 0
    midpoint = rcon_start + (rcon_end - rcon_start) / 2
    score += 2 if board_start <= midpoint <= board_end else 0
    edge = min(
        abs((rcon_start - board_start).total_seconds()),
        abs((rcon_start - board_end).total_seconds()),
        abs((rcon_end - board_start).total_seconds()),
        abs((rcon_end - board_end).total_seconds()),
    )
    score += 2 if edge <= 1800 else 1 if edge <= 3600 else 0
    rcon_duration = int((rcon_end - rcon_start).total_seconds())
    board_duration = int((board_end - board_start).total_seconds())
    score += int(abs(rcon_duration - board_duration) <= 1800)
    allied = rcon.get("allied_score")
    axis = rcon.get("axis_score")
    board_allied = scoreboard.get("allied_score")
    board_axis = scoreboard.get("axis_score")
    if None not in (allied, axis, board_allied, board_axis):
        if (as_int(allied), as_int(axis)) == (as_int(board_allied), as_int(board_axis)):
            score += 2
        elif sorted((as_int(allied), as_int(axis))) == sorted((as_int(board_allied), as_int(board_axis))):
            score += 1
    return score if score > 0 else None


def mutual_unique_best_assignments(
    edges_by_board: Mapping[int, Sequence[tuple[int, str]]],
) -> tuple[dict[int, str], dict[int, set[str]]]:
    """Return mutual unique-best one-to-one links and ambiguous top candidates."""

    board_top: dict[int, set[str]] = {}
    rcon_edges: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for board_index, edges in edges_by_board.items():
        if not edges:
            continue
        best_score = max(score for score, _ in edges)
        board_top[board_index] = {key for score, key in edges if score == best_score}
        for score, key in edges:
            rcon_edges[key].append((score, board_index))

    rcon_top: dict[str, set[int]] = {}
    for key, edges in rcon_edges.items():
        best_score = max(score for score, _ in edges)
        rcon_top[key] = {board_index for score, board_index in edges if score == best_score}

    exact: dict[int, str] = {}
    ambiguous: dict[int, set[str]] = {}
    for board_index, candidates in board_top.items():
        if len(candidates) == 1:
            key = next(iter(candidates))
            if rcon_top.get(key) == {board_index}:
                exact[board_index] = key
                continue
        ambiguous[board_index] = candidates
    return exact, ambiguous


def audit_scoreboard_parity(
    db: ReadOnlyDatabase,
    resolver: TargetResolver,
    selected_servers: set[str],
    derived: list[dict[str, object]],
    windows: list[dict[str, object]],
) -> dict[str, object]:
    scoreboard: dict[str, list[dict[str, object]]] = {slug: [] for slug in selected_servers}
    scoreboard_inventory = {
        "all_servers_total": 0,
        "trusted_01_02_total": 0,
        "excluded_other_servers_total": 0,
    }
    if db.table_exists("historical_matches") and db.table_exists("historical_servers"):
        inventory_row = db.execute(
            """
            SELECT COUNT(*) AS all_servers_total,
                   COALESCE(SUM(CASE WHEN hs.slug IN ('comunidad-hispana-01', 'comunidad-hispana-02')
                                     THEN 1 ELSE 0 END), 0) AS trusted_01_02_total,
                   COALESCE(SUM(CASE WHEN hs.slug NOT IN ('comunidad-hispana-01', 'comunidad-hispana-02')
                                     THEN 1 ELSE 0 END), 0) AS excluded_other_servers_total
            FROM historical_matches AS hm
            JOIN historical_servers AS hs ON hs.id = hm.historical_server_id
            """
        ).fetchone()
        if inventory_row:
            inventory_values = dict(inventory_row)
            scoreboard_inventory = {
                key: as_int(inventory_values.get(key))
                for key in scoreboard_inventory
            }
        for row in db.iterate(
            """
            SELECT hs.slug, hm.id, hm.started_at, hm.ended_at, hm.map_name,
                   hm.map_pretty_name, hm.game_mode, hm.allied_score, hm.axis_score
            FROM historical_matches AS hm
            JOIN historical_servers AS hs ON hs.id = hm.historical_server_id
            WHERE hs.slug IN ('comunidad-hispana-01', 'comunidad-hispana-02')
            ORDER BY hs.slug, COALESCE(hm.ended_at, hm.started_at), hm.id
            """
        ):
            slug = str(row.get("slug") or "")
            if slug in selected_servers:
                scoreboard[slug].append(row)

    result: dict[str, object] = {}
    match_correlations: dict[str, str] = {}
    for slug in sorted(selected_servers):
        rcon = [
            {**row, "server": resolver.resolve(row.get("target_key"), row.get("external_server_id"))}
            for row in derived
            if resolver.resolve(row.get("target_key"), row.get("external_server_id")) == slug
            and bound_class(row) == "both_bounds"
            and match_time_bounds(row)[0]
            and match_time_bounds(row)[1]
        ]
        boards = [
            row for row in scoreboard[slug]
            if parse_timestamp(row.get("started_at")) and parse_timestamp(row.get("ended_at"))
        ]
        scoreboard_starts = [
            parsed
            for row in boards
            if (parsed := parse_timestamp(row.get("started_at"))) is not None
        ]
        scoreboard_ends = [
            parsed
            for row in boards
            if (parsed := parse_timestamp(row.get("ended_at"))) is not None
        ]
        rcon_times = [match_time_bounds(row)[0] for row in rcon] + [match_time_bounds(row)[1] for row in rcon]
        board_times = [parse_timestamp(row.get("started_at")) for row in boards] + [parse_timestamp(row.get("ended_at")) for row in boards]
        rcon_times = [value for value in rcon_times if value]
        board_times = [value for value in board_times if value]
        overlap_start = max(min(rcon_times), min(board_times)) if rcon_times and board_times else None
        overlap_end = min(max(rcon_times), max(board_times)) if rcon_times and board_times else None
        if overlap_start and overlap_end and overlap_end >= overlap_start:
            boards_in_range = [
                row for row in boards
                if (end := match_time_bounds(row)[1]) and overlap_start <= end <= overlap_end
            ]
            rcon_in_range = [
                row for row in rcon
                if (end := match_time_bounds(row)[1]) and overlap_start <= end <= overlap_end
            ]
        else:
            boards_in_range = []
            rcon_in_range = []

        for row in rcon:
            ref = safe_ref("match", row.get("match_key"))
            end = match_time_bounds(row)[1]
            match_correlations[ref] = (
                "no-scoreboard-counterpart"
                if overlap_start and overlap_end and end and overlap_start <= end <= overlap_end
                else "outside-comparable-scoreboard-coverage"
            )

        classifications = Counter()
        selected_rcon_refs: set[str] = set()
        rcon_by_key = {str(row.get("match_key") or ""): row for row in rcon_in_range}
        edges_by_board: dict[int, list[tuple[int, str]]] = {}
        for board_index, board in enumerate(boards_in_range):
            edges_by_board[board_index] = [
                (score, str(row.get("match_key") or ""))
                for row in rcon_in_range
                if (score := candidate_score(row, board)) is not None and score >= 5
            ]
        exact_assignments, ambiguous_assignments = mutual_unique_best_assignments(edges_by_board)

        for board_index, board in enumerate(boards_in_range):
            if board_index in exact_assignments:
                classifications["exact_rcon_match"] += 1
                selected_ref = safe_ref("match", exact_assignments[board_index])
                selected_rcon_refs.add(selected_ref)
                match_correlations[selected_ref] = "exact-scoreboard-match"
                continue
            if board_index in ambiguous_assignments:
                classifications["ambiguous"] += 1
                for candidate_key in sorted(ambiguous_assignments[board_index]):
                    if candidate_key not in rcon_by_key:
                        continue
                    match_correlations[safe_ref("match", candidate_key)] = (
                        "ambiguous-scoreboard-candidate"
                    )
                continue
            board_start = parse_timestamp(board.get("started_at"))
            board_end = parse_timestamp(board.get("ended_at"))
            partial_candidate = False
            for window in windows:
                if window.get("server") != slug:
                    continue
                if normalize_window_map(window) != normalize_map_name(board.get("map_pretty_name") or board.get("map_name")):
                    continue
                win_start = parse_timestamp(window.get("first_seen_at"))
                win_end = parse_timestamp(window.get("last_seen_at"))
                if board_start and board_end and win_start and win_end:
                    edge = min(
                        abs((board_start - win_start).total_seconds()),
                        abs((board_start - win_end).total_seconds()),
                        abs((board_end - win_start).total_seconds()),
                        abs((board_end - win_end).total_seconds()),
                    )
                    if min(board_end, win_end) >= max(board_start, win_start) or edge <= 3600:
                        partial_candidate = True
                        break
            classifications["partial_or_session_only" if partial_candidate else "missing_rcon_counterpart"] += 1

        windows_ended_in_range = 0
        windows_overlapping_range = 0
        if overlap_start and overlap_end:
            for window in windows:
                if window.get("server") != slug:
                    continue
                window_start = parse_timestamp(window.get("first_seen_at"))
                window_end = parse_timestamp(window.get("last_seen_at"))
                if not window_start or not window_end:
                    continue
                windows_ended_in_range += int(overlap_start <= window_end <= overlap_end)
                windows_overlapping_range += int(
                    min(overlap_end, window_end) >= max(overlap_start, window_start)
                )
        result[slug] = {
            "scoreboard_total": len(scoreboard[slug]),
            "scoreboard_parseable_windows": len(boards),
            "scoreboard_full_coverage": {
                "started_at": [
                    min(scoreboard_starts).isoformat().replace("+00:00", "Z") if scoreboard_starts else None,
                    max(scoreboard_starts).isoformat().replace("+00:00", "Z") if scoreboard_starts else None,
                ],
                "ended_at": [
                    min(scoreboard_ends).isoformat().replace("+00:00", "Z") if scoreboard_ends else None,
                    max(scoreboard_ends).isoformat().replace("+00:00", "Z") if scoreboard_ends else None,
                ],
            },
            "derived_rcon_both_bounds": len(rcon),
            "overlap_coverage": {
                "start": overlap_start.isoformat().replace("+00:00", "Z") if overlap_start else None,
                "end": overlap_end.isoformat().replace("+00:00", "Z") if overlap_end else None,
            },
            "scoreboard_matches_in_overlap": len(boards_in_range),
            "rcon_matches_in_overlap": len(rcon_in_range),
            "competitive_windows_ended_in_overlap": windows_ended_in_range,
            "competitive_windows_overlapping_range": windows_overlapping_range,
            "classifications": dict(classifications),
            "rcon_without_selected_scoreboard_counterpart": max(0, len(rcon_in_range) - len(selected_rcon_refs)),
            "method": "complete persisted scoreboard history; same normalized map, score >=5, mutual unique-best one-to-one assignment",
        }
    result["persisted_scoreboard_inventory"] = scoreboard_inventory
    result["match_correlations"] = match_correlations
    return result


def render_markdown(result: Mapping[str, object]) -> str:
    lines = [
        "# TASK-287 deterministic diagnostic summary",
        "",
        f"- Schema: `{result.get('schema_version')}`",
        f"- Backend: `{result.get('execution', {}).get('backend')}`",
        f"- Read-only: `{result.get('execution', {}).get('read_only')}`",
        "",
        "## Server inventory",
        "",
        "| Server | AdminLog events | Materialized matches | Scoreboard matches |",
        "| --- | ---: | ---: | ---: |",
    ]
    servers = result.get("servers", {})
    materialized = result.get("materialized", {})
    parity = result.get("scoreboard_parity", {})
    if isinstance(servers, dict):
        for slug in sorted(servers):
            server = servers[slug]
            lines.append(
                f"| {slug} | {server.get('admin_log', {}).get('total_events', 0)} "
                f"| {materialized.get(slug, {}).get('total', 0)} "
                f"| {parity.get(slug, {}).get('scoreboard_total', 0)} |"
            )
    lines.extend(["", "Full aggregate evidence is available in deterministic JSON output.", ""])
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--sqlite", type=Path, help="SQLite database path opened with mode=ro")
    source.add_argument("--postgres-env", help="Environment variable containing the PostgreSQL DSN")
    parser.add_argument("--sqlite-immutable", action="store_true", help="Use only for an offline SQLite snapshot with no WAL writes")
    parser.add_argument("--target-config-env-file", type=Path, help="Optional env file used only to map configured hosts to public server slugs")
    parser.add_argument("--server", action="append", choices=sorted(TRUSTED_SERVERS), help="Trusted server slug; repeatable")
    parser.add_argument(
        "--from",
        dest="from_timestamp",
        help="Inclusive event_timestamp bound for the requested-range AdminLog inventory",
    )
    parser.add_argument(
        "--until",
        dest="until_timestamp",
        help="Exclusive event_timestamp bound for the requested-range AdminLog inventory",
    )
    parser.add_argument("--task271-split-at", help="ISO-8601 reference for pre/post acquisition eras")
    parser.add_argument("--max-sanitized-examples", type=int, default=5)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path, help="Optional output path; stdout when omitted")
    return parser.parse_args(argv)


def validate_cli(args: argparse.Namespace) -> tuple[set[str], datetime | None, datetime | None, datetime | None]:
    selected = set(args.server or TRUSTED_SERVERS)
    from_timestamp = parse_timestamp(args.from_timestamp)
    until_timestamp = parse_timestamp(args.until_timestamp)
    split_at = parse_timestamp(args.task271_split_at)
    if args.from_timestamp and from_timestamp is None:
        raise SystemExit("--from must be valid ISO-8601")
    if args.until_timestamp and until_timestamp is None:
        raise SystemExit("--until must be valid ISO-8601")
    if from_timestamp and until_timestamp and until_timestamp <= from_timestamp:
        raise SystemExit("--until must be after --from")
    if args.max_sanitized_examples < 0 or args.max_sanitized_examples > 50:
        raise SystemExit("--max-sanitized-examples must be between 0 and 50")
    if args.sqlite_immutable and args.sqlite is None:
        raise SystemExit("--sqlite-immutable requires --sqlite")
    return selected, from_timestamp, until_timestamp, split_at


def run_audit(args: argparse.Namespace) -> dict[str, object]:
    selected, from_timestamp, until_timestamp, split_at = validate_cli(args)
    db = (
        open_sqlite_read_only(args.sqlite, immutable=args.sqlite_immutable)
        if args.sqlite
        else open_postgres_read_only(args.postgres_env)
    )
    try:
        required = (
            "rcon_admin_log_events",
            "rcon_materialized_matches",
            "rcon_match_player_stats",
            "rcon_historical_competitive_windows",
            "rcon_historical_samples",
            "rcon_historical_targets",
        )
        missing = [table for table in required if not db.table_exists(table)]
        if missing:
            raise RuntimeError("required audit tables are unavailable: " + ", ".join(missing))
        resolver = build_target_resolver(db, args.target_config_env_file)
        servers, event_target_keys = audit_inventory(db, resolver, selected)
        requested_range_inventory = audit_requested_event_range(
            db, resolver, selected, from_timestamp, until_timestamp
        )
        boundaries = read_boundaries(db, resolver, selected)
        derived, boundary_sequences = derive_admin_matches(
            boundaries,
            resolver,
            selected,
            nulls_last=db.dialect == "postgres",
        )
        boundary_ordering = audit_boundary_ordering(boundaries, resolver, selected)
        persisted = read_materialized_matches(db, resolver, selected)
        stat_aggregates = read_stat_aggregates(db)
        materialized, range_metrics, overlap = summarize_materialized(
            persisted, derived, boundaries, db, resolver, selected
        )
        invariants, top_lists, confirmed_inflated, partial_rows, match_statistics = audit_stats_and_toplists(
            persisted, range_metrics, stat_aggregates, boundaries, derived
        )
        fallback, stale, windows, derived_fallback = audit_windows_and_stale(
            db, resolver, selected, persisted, derived, range_metrics
        )
        merging = audit_competitive_merging(db, resolver, selected, windows, boundaries)
        parser = audit_parser(db, resolver, selected, args.max_sanitized_examples)
        dedupe = audit_dedupe(db, resolver, selected)
        acquisition = audit_acquisition(db, resolver, selected, split_at)
        parity = audit_scoreboard_parity(db, resolver, selected, derived, windows)
        match_correlations = parity.pop("match_correlations", {})
        for rows in [*top_lists.values(), confirmed_inflated, partial_rows, match_statistics]:
            for row in rows:
                ref = str(row.get("match_ref") or "")
                if ref in match_correlations:
                    row["scoreboard_correlation"] = match_correlations[ref]
                elif row.get("bounds") in {"lower_only", "upper_only"}:
                    row["scoreboard_correlation"] = "unavailable-partial-bounds"
                elif row.get("bounds") == "no_bounds":
                    row["scoreboard_correlation"] = "session-fallback-not-exact"
                else:
                    row["scoreboard_correlation"] = "not-correlated"
        for slug in selected:
            servers[slug]["materialized"] = materialized.get(slug, {})
            servers[slug]["competitive_windows"] = fallback.get("by_server", {}).get(slug, {})
            servers[slug]["scoreboard"] = parity.get(slug, {})
        return {
            "schema_version": SCHEMA_VERSION,
            "execution": {
                "backend": db.dialect,
                "read_only": True,
                "database_ref": db.source_ref,
                "servers": sorted(selected),
                "requested_range": {
                    "from_inclusive": from_timestamp.isoformat().replace("+00:00", "Z") if from_timestamp else None,
                    "until_exclusive": until_timestamp.isoformat().replace("+00:00", "Z") if until_timestamp else None,
                },
                "note": "Unbounded materializer semantics are audited over the full stored target history.",
                "requested_range_semantics": (
                    "from/until filter requested_range_admin_log_inventory by event_timestamp only; "
                    "causal range/overlap/stale analyses stay full-history to reproduce unbounded predicates"
                ),
                "boundary_null_order": "NULLS LAST" if db.dialect == "postgres" else "NULLS FIRST",
            },
            "servers": servers,
            "requested_range_admin_log_inventory": requested_range_inventory,
            "boundary_sequences": boundary_sequences,
            "boundary_ordering": boundary_ordering,
            "materialized": materialized,
            "overlap": overlap,
            "invariants": invariants,
            "confirmed_inflated_matches": confirmed_inflated,
            "partial_unbounded_matches": partial_rows,
            "match_statistics": match_statistics,
            "top20": top_lists,
            "fallback": fallback,
            "stale_materialized": stale,
            "competitive_window_merging": merging,
            "parser": parser,
            "dedupe": dedupe,
            "acquisition": acquisition,
            "scoreboard_parity": parity,
            "limitations": [
                "Production counts require execution against the deployed PostgreSQL schema in a read-only transaction.",
                "Persisted rows cannot prove which observations were rejected by dedupe without independent pre-persistence evidence.",
                "Observed event gaps alone cannot prove that an AdminLog poll failed.",
                "Fallback suppression and merge signals are candidates until independently correlated to real rounds.",
            ],
        }
    finally:
        db.close()


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_audit(args)
    assert_public_result_is_sanitized(result)
    rendered = (
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        if args.format == "json"
        else render_markdown(result)
    )
    if args.output:
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
