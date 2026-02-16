-- AI Brain: Phase 2 — Collectors, Publishing, Scheduling, Quality Gate
-- Migration 002

-- ── Ideas Table (from real collectors) ──
CREATE TYPE idea_source AS ENUM (
    'youtube_trending',
    'youtube_search',
    'rss_feed',
    'reddit',
    'gpt_research',
    'manual'
);

CREATE TYPE idea_status AS ENUM (
    'NEW',
    'RANKED',
    'SELECTED',
    'USED',
    'REJECTED'
);

CREATE TABLE ideas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id        UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    source          idea_source NOT NULL,
    source_url      TEXT,
    source_metadata JSONB,
    -- { channel_id, subreddit, feed_url, video_id, upvotes, view_count, etc. }

    title           TEXT NOT NULL,
    description     TEXT,
    keywords        TEXT[] DEFAULT '{}',
    relevance_score NUMERIC(5,3),
    -- AI-ranked 0.000-1.000

    status          idea_status NOT NULL DEFAULT 'NEW',
    used_by_job_id  UUID REFERENCES jobs(id),

    collected_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,
    -- ideas go stale; default 72h from collection

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ideas_brand_status ON ideas(brand_id, status);
CREATE INDEX idx_ideas_relevance ON ideas(brand_id, relevance_score DESC) WHERE status = 'NEW' OR status = 'RANKED';
CREATE INDEX idx_ideas_source ON ideas(source, collected_at DESC);
CREATE INDEX idx_ideas_expires ON ideas(expires_at) WHERE status IN ('NEW', 'RANKED');

-- ── Publish Slots (slot-based scheduling) ──
CREATE TABLE publish_slots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id        UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    platform        platform_type NOT NULL,
    day_of_week     SMALLINT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    -- 0=Sunday, 6=Saturday
    publish_hour    SMALLINT NOT NULL CHECK (publish_hour BETWEEN 0 AND 23),
    publish_minute  SMALLINT NOT NULL DEFAULT 0 CHECK (publish_minute BETWEEN 0 AND 59),
    timezone        VARCHAR(50) NOT NULL DEFAULT 'America/New_York',
    jitter_minutes  SMALLINT NOT NULL DEFAULT 10 CHECK (jitter_minutes BETWEEN 0 AND 30),
    -- random ± jitter applied at scheduling time
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    priority        SMALLINT NOT NULL DEFAULT 1,
    -- higher = more important slot

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_slot UNIQUE (brand_id, platform, day_of_week, publish_hour)
);

CREATE INDEX idx_slots_active ON publish_slots(brand_id, platform, day_of_week) WHERE is_active = TRUE;

-- ── Quality Check Results ───────────────
CREATE TYPE quality_check_status AS ENUM (
    'PASSED',
    'WARNED',
    'FAILED'
);

CREATE TABLE quality_checks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    check_name      VARCHAR(100) NOT NULL,
    status          quality_check_status NOT NULL,
    details         JSONB,
    -- actionable failure reason
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_quality_check UNIQUE (job_id, check_name)
);

CREATE INDEX idx_quality_job ON quality_checks(job_id);

-- ── Collector Configs (per-brand feed sources) ──
CREATE TABLE collector_configs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id        UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    source          idea_source NOT NULL,
    config          JSONB NOT NULL,
    -- youtube_search: { keywords: [], channels: [], recency_days: 7 }
    -- rss_feed:      { feeds: [{ url, label }] }
    -- reddit:        { subreddits: [], min_upvotes: 50, sort: "hot" }
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_run_at     TIMESTAMPTZ,
    run_interval_minutes INTEGER NOT NULL DEFAULT 360,
    -- default: every 6 hours

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_collector_config UNIQUE (brand_id, source)
);

-- ── Expand brands table ─────────────────
ALTER TABLE brands
    ADD COLUMN IF NOT EXISTS hashtag_bank JSONB DEFAULT '[]',
    -- per-platform: { youtube: ["#shorts"], tiktok: [...], instagram: [...] }
    ADD COLUMN IF NOT EXISTS forbidden_words TEXT[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS topic_keywords TEXT[] DEFAULT '{}',
    -- seed keywords for collectors
    ADD COLUMN IF NOT EXISTS posting_cadence JSONB DEFAULT '{}',
    -- { youtube: { max_per_day: 2 }, tiktok: { max_per_day: 3 }, ... }
    ADD COLUMN IF NOT EXISTS music_pack JSONB DEFAULT '[]',
    -- [ { name, s3_url, bpm, mood, duration_s } ]
    ADD COLUMN IF NOT EXISTS font_variants JSONB DEFAULT '{}',
    -- { heading: "Inter-Bold", body: "Inter-Regular", accent: "Montserrat-Bold" }
    ADD COLUMN IF NOT EXISTS safe_margins JSONB DEFAULT '{"top_px": 200, "bottom_px": 180, "left_px": 40, "right_px": 40}',
    -- per-platform UI overlay safe zones
    ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'America/New_York';

-- ── Expand jobs table ───────────────────
ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS idea_id UUID REFERENCES ideas(id),
    ADD COLUMN IF NOT EXISTS scheduled_publish_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS actual_publish_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS quality_passed BOOLEAN,
    ADD COLUMN IF NOT EXISTS slot_id UUID REFERENCES publish_slots(id);

-- ── Add layout_variant to bandit arms (new dimension) ──
-- This is handled via seed data, not schema change

-- ── Publish attempts log ────────────────
CREATE TABLE publish_attempts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    platform        platform_type NOT NULL,
    attempt_number  SMALLINT NOT NULL DEFAULT 1,
    status          VARCHAR(20) NOT NULL,
    -- 'POSTED', 'DRAFTED', 'QUEUED', 'FAILED'
    platform_response JSONB,
    error_message   TEXT,
    attempted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_publish_attempts_job ON publish_attempts(job_id);

-- ── Alert rules table ───────────────────
CREATE TABLE alert_rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL UNIQUE,
    rule_type       VARCHAR(50) NOT NULL,
    -- 'no_post_by_time', 'budget_exceeded', 'budget_projected', 'stale_job', 'dlq_depth'
    config          JSONB NOT NULL,
    -- { check_time: "10:30", timezone: "America/New_York" }
    -- { threshold_percent: 90 }
    webhook_url     TEXT,
    -- Discord/Slack/email webhook
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_triggered  TIMESTAMPTZ,
    cooldown_minutes INTEGER NOT NULL DEFAULT 60,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Triggers ────────────────────────────
CREATE TRIGGER trg_ideas_updated_at
    BEFORE UPDATE ON ideas FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_publish_slots_updated_at
    BEFORE UPDATE ON publish_slots FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_collector_configs_updated_at
    BEFORE UPDATE ON collector_configs FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_alert_rules_updated_at
    BEFORE UPDATE ON alert_rules FOR EACH ROW EXECUTE FUNCTION update_updated_at();
