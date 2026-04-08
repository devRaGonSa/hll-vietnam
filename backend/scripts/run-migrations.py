"""Apply staged PostgreSQL SQL-first migrations for the backend."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    backend_root = Path(__file__).resolve().parents[1]
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    from app.postgres_utils import apply_postgres_migrations, probe_postgres_connection

    probe = probe_postgres_connection()
    results = apply_postgres_migrations()
    print(
        json.dumps(
            {
                "status": "ok",
                "database_name": probe["database_name"],
                "user_name": probe["user_name"],
                "migration_count": len(results),
                "migrations": results,
            },
            ensure_ascii=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
