ALTER TABLE historical_matches
    ADD COLUMN IF NOT EXISTS detail_status TEXT NOT NULL DEFAULT 'partial';

ALTER TABLE historical_matches
    ADD COLUMN IF NOT EXISTS detail_quality_reason TEXT;

ALTER TABLE historical_matches
    ADD COLUMN IF NOT EXISTS detail_last_attempt_at TIMESTAMPTZ;

ALTER TABLE historical_matches
    ADD COLUMN IF NOT EXISTS detail_last_error TEXT;

ALTER TABLE historical_matches
    ADD COLUMN IF NOT EXISTS detail_retry_count INTEGER NOT NULL DEFAULT 0;

UPDATE historical_matches
SET detail_status = CASE
        WHEN started_at IS NOT NULL
         AND ended_at IS NOT NULL
         AND started_at < ended_at
         AND allied_score IS NOT NULL
         AND axis_score IS NOT NULL
        THEN 'complete'
        ELSE 'partial'
    END,
    detail_quality_reason = CASE
        WHEN started_at IS NOT NULL
         AND ended_at IS NOT NULL
         AND started_at < ended_at
         AND allied_score IS NOT NULL
         AND axis_score IS NOT NULL
        THEN NULL
        ELSE COALESCE(detail_quality_reason, 'legacy-row-needs-repair-evaluation')
    END
WHERE detail_status IS NULL
   OR detail_status = 'partial';

CREATE INDEX IF NOT EXISTS idx_historical_matches_detail_repair
    ON historical_matches (detail_status, ended_at DESC, started_at DESC);
