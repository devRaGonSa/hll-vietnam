"""Regression coverage for API JSON encoding of PostgreSQL value types."""

from __future__ import annotations

import json
import unittest
from datetime import date, datetime, timezone

from app.main import _json_default


class JsonSerializationTests(unittest.TestCase):
    def test_json_default_serializes_postgres_datetime_and_date_values(self) -> None:
        payload = {
            "started_at": datetime(2026, 5, 21, 10, 11, 12, tzinfo=timezone.utc),
            "day": date(2026, 5, 21),
        }

        encoded = json.loads(json.dumps(payload, default=_json_default))

        self.assertEqual(
            encoded,
            {
                "started_at": "2026-05-21T10:11:12+00:00",
                "day": "2026-05-21",
            },
        )
