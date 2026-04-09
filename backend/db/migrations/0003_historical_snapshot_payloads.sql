CREATE TABLE IF NOT EXISTS historical_snapshot_payloads (
    id BIGSERIAL PRIMARY KEY,
    server_key TEXT NOT NULL,
    snapshot_type TEXT NOT NULL,
    metric TEXT,
    snapshot_window TEXT,
    identity_metric TEXT GENERATED ALWAYS AS (COALESCE(metric, '')) STORED,
    identity_window TEXT GENERATED ALWAYS AS (COALESCE(snapshot_window, '')) STORED,
    payload_json JSONB NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    source_range_start TIMESTAMPTZ,
    source_range_end TIMESTAMPTZ,
    is_stale BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_historical_snapshot_payload_identity
    ON historical_snapshot_payloads (
        server_key,
        snapshot_type,
        identity_metric,
        identity_window
    );

CREATE INDEX IF NOT EXISTS idx_historical_snapshot_payload_generated_at
    ON historical_snapshot_payloads (generated_at DESC);
