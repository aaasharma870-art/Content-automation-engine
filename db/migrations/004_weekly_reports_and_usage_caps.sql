-- AI Brain: Phase 4 — Weekly Reports, Usage Caps, Bandit Kill Switch
-- Migration 004

-- ── Asset usage tracking (rolling 30-day caps) ──
CREATE TABLE asset_usage_daily (
    id          SERIAL PRIMARY KEY,
    brand_id    UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    usage_date  DATE NOT NULL DEFAULT CURRENT_DATE,
    dalle_count INTEGER NOT NULL DEFAULT 0,
    tts_count   INTEGER NOT NULL DEFAULT 0,
    stock_video_count INTEGER NOT NULL DEFAULT 0,
    stock_image_count INTEGER NOT NULL DEFAULT 0,
    cache_count INTEGER NOT NULL DEFAULT 0,
    total_count INTEGER NOT NULL DEFAULT 0,
    dalle_cost_usd  NUMERIC(10,4) DEFAULT 0,
    tts_cost_usd    NUMERIC(10,4) DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_asset_usage UNIQUE (brand_id, usage_date)
);

CREATE INDEX idx_asset_usage_brand ON asset_usage_daily(brand_id, usage_date DESC);

-- ── Weekly reports table ──────────────
CREATE TABLE weekly_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id        UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    report_week     DATE NOT NULL,
    -- Monday of the report week
    top_posts       JSONB NOT NULL DEFAULT '[]',
    -- [{job_id, content_type, hook_archetype, visual_family, music_style, metrics: {...}}]
    bottom_posts    JSONB NOT NULL DEFAULT '[]',
    shared_traits   JSONB NOT NULL DEFAULT '{}',
    -- {top: {common_content_types: [...], common_archetypes: [...]}, bottom: {...}}
    recommendations JSONB NOT NULL DEFAULT '[]',
    -- ["Increase pov_poetry posts", "Reduce bold_claim hooks", ...]
    summary_text    TEXT,
    total_posts     INTEGER DEFAULT 0,
    avg_hold_rate   NUMERIC(5,3),
    avg_shares_per_view NUMERIC(8,6),
    avg_completion_rate NUMERIC(5,3),
    sent_to         JSONB DEFAULT '[]',
    -- ["discord", "email"]
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_weekly_report UNIQUE (brand_id, report_week)
);

CREATE INDEX idx_weekly_reports_brand ON weekly_reports(brand_id, report_week DESC);

-- ── Bandit kill switch tracking ───────
ALTER TABLE bandit_arms
    ADD COLUMN IF NOT EXISTS consecutive_underperforms INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS killed_until TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS kill_count INTEGER NOT NULL DEFAULT 0;

-- ── Expand analytics_snapshots for detailed metrics ──
ALTER TABLE analytics_snapshots
    ADD COLUMN IF NOT EXISTS saves INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS follows INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS hold_rate_2s NUMERIC(5,3),
    ADD COLUMN IF NOT EXISTS completion_rate NUMERIC(5,3),
    ADD COLUMN IF NOT EXISTS shares_per_view NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS comments_per_view NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS follows_per_view NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS likes_per_view NUMERIC(8,6);

-- ── Expand brands for asset finder API keys ──
ALTER TABLE brands
    ADD COLUMN IF NOT EXISTS pexels_api_key TEXT,
    ADD COLUMN IF NOT EXISTS pixabay_api_key TEXT,
    ADD COLUMN IF NOT EXISTS unsplash_api_key TEXT;

-- ── Trigger for asset_usage_daily ─────
CREATE TRIGGER trg_asset_usage_updated_at
    BEFORE UPDATE ON asset_usage_daily FOR EACH ROW EXECUTE FUNCTION update_updated_at();
