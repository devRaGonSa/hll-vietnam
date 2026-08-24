from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]


class HistoricalPlayerCountFrontendTests(unittest.TestCase):
    def test_null_undefined_unknown_and_confirmed_zero_render_distinctly(self):
        source = (ROOT / "frontend/assets/js/historico.js").read_text(encoding="utf-8")
        match = re.search(
            r"function formatPlayerCount\(value, status\) \{.*?\n\}",
            source,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)
        formatter = match.group(0)
        unavailable_guard = (
            'value === null || value === undefined || normalizedStatus.startsWith("unknown")'
        )
        self.assertIn(unavailable_guard, formatter)
        self.assertIn('return "No disponible";', formatter)
        self.assertIn("Number.isInteger(parsedValue)", formatter)
        self.assertIn("parsedValue < 0", formatter)
        self.assertLess(formatter.index(unavailable_guard), formatter.index("Number(value)"))
        self.assertIn(
            "formatPlayerCount(item.player_count, item.player_count_status)",
            source,
        )


if __name__ == "__main__":
    unittest.main()
