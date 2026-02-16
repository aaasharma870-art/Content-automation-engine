-- AI Brain: Initial Schema
-- Migration 001

-- ── Extensions ──────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Enums ───────────────────────────────
CREATE TYPE job_state AS ENUM (
    'QUEUED',
    'RESEARCHING',
    'WRITING',
    'AUDITING',
    'RENDERING',
    'UPLOADING',
    'POSTED',
    'DRAFTED',
    'ANALYZED',
    'FAILED'
);

CREATE TYPE platform_type AS ENUM (
    'youtube',
    'tiktok',
    'instagram'
);

CREATE TYPE risk_flag AS ENUM (
    'NONE',
    'LOW',
    'MEDIUM',
    'HIGH',
    'BLOCKED'
);

-- ── Brands ──────────────────────────────
CREATE TABLE brands (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL UNIQUE,
    palette         JSONB NOT NULL DEFAULT '[]',
    font_family     VARCHAR(100) NOT NULL DEFAULT 'Inter',
    motion_profile  VARCHAR(50) NOT NULL DEFAULT 'smooth',
    music_bias      VARCHAR(50) NOT NULL DEFAULT 'upbeat',
    logo_s3_url     TEXT,
    version         INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Bandit Arms ─────────────────────────
CREATE TABLE bandit_arms (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id        UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    dimension       VARCHAR(50) NOT NULL,
    variant         VARCHAR(100) NOT NULL,
    alpha           NUMERIC(10,4) NOT NULL DEFAULT 1.0,
    beta            NUMERIC(10,4) NOT NULL DEFAULT 1.0,
    total_pulls     INTEGER NOT NULL DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_arm UNIQUE (brand_id, dimension, variant)
);

CREATE INDEX idx_bandit_active ON bandit_arms(brand_id, dimension) WHERE is_active = TRUE;

-- ── Jobs ────────────────────────────────
CREATE TABLE jobs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id            UUID NOT NULL REFERENCES brands(id),
    state               job_state NOT NULL DEFAULT 'QUEUED',
    platform            platform_type NOT NULL,
    platform_target_date DATE NOT NULL,

    -- Content (populated as pipeline progresses)
    topic               TEXT,
    research_data       JSONB,
    script              JSONB,
    art_prompts         TEXT[],
    art_urls            TEXT[],
    audio_url           TEXT,
    video_url           TEXT,

    -- Platform result
    platform_post_id    TEXT,
    platform_post_url   TEXT,
    publish_status      VARCHAR(20),

    -- Policy gate result
    policy_approved     BOOLEAN,
    policy_risk_flag    risk_flag,
    policy_reason       TEXT,

    -- Bandit experiment tracking
    bandit_arm_id       UUID REFERENCES bandit_arms(id),
    bandit_selections   JSONB,

    -- Idempotency
    content_hash        VARCHAR(64),

    -- Retry tracking
    attempt_count       INTEGER NOT NULL DEFAULT 0,
    max_attempts        INTEGER NOT NULL DEFAULT 3,
    last_error          TEXT,
    failed_at_state     job_state,

    -- Cost tracking
    openai_cost_usd     NUMERIC(10,6) DEFAULT 0,
    render_duration_ms  INTEGER,

    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT uq_platform_target UNIQUE (brand_id, platform, platform_target_date),
    CONSTRAINT uq_content_hash UNIQUE (content_hash)
);

CREATE INDEX idx_jobs_state ON jobs(state);
CREATE INDEX idx_jobs_brand_id ON jobs(brand_id);
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX idx_jobs_platform_date ON jobs(platform, platform_target_date);

-- ── Job State Log (audit trail) ─────────
CREATE TABLE job_state_log (
    id          BIGSERIAL PRIMARY KEY,
    job_id      UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    from_state  job_state,
    to_state    job_state NOT NULL,
    message     TEXT,
    meta        JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_state_log_job_id ON job_state_log(job_id);

-- ── Dead Letter Queue ───────────────────
CREATE TABLE dead_letter_queue (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    failed_state    job_state NOT NULL,
    error_message   TEXT NOT NULL,
    error_stack     TEXT,
    attempt_count   INTEGER NOT NULL,
    meta            JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ,
    resolved_by     VARCHAR(100)
);

CREATE INDEX idx_dlq_unresolved ON dead_letter_queue(created_at) WHERE resolved_at IS NULL;

-- ── Bandit Rewards ──────────────────────
CREATE TABLE bandit_rewards (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    arm_id      UUID NOT NULL REFERENCES bandit_arms(id) ON DELETE CASCADE,
    job_id      UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    reward      NUMERIC(8,4) NOT NULL,
    raw_metrics JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rewards_arm ON bandit_rewards(arm_id);

-- ── Art Cache ───────────────────────────
CREATE TABLE art_cache (
    prompt_hash VARCHAR(64) PRIMARY KEY,
    prompt_text TEXT NOT NULL,
    s3_url      TEXT NOT NULL,
    width       INTEGER,
    height      INTEGER,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Daily Spend ─────────────────────────
CREATE TABLE daily_spend (
    id          SERIAL PRIMARY KEY,
    spend_date  DATE NOT NULL DEFAULT CURRENT_DATE,
    brand_id    UUID NOT NULL REFERENCES brands(id),
    amount_usd  NUMERIC(10,4) NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_daily_spend UNIQUE (spend_date, brand_id)
);

CREATE INDEX idx_spend_date ON daily_spend(spend_date DESC);

-- ── Platform Credentials ────────────────
CREATE TABLE platform_credentials (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id         UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    platform         platform_type NOT NULL,
    access_token     TEXT NOT NULL,
    refresh_token    TEXT,
    token_expires_at TIMESTAMPTZ,
    channel_id       VARCHAR(200),
    meta             JSONB,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_brand_platform UNIQUE (brand_id, platform)
);

-- ── Blocklists ──────────────────────────
CREATE TABLE blocklists (
    id          SERIAL PRIMARY KEY,
    category    VARCHAR(50) NOT NULL,
    term        VARCHAR(500) NOT NULL,
    is_regex    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_blocklist UNIQUE (category, term)
);

CREATE INDEX idx_blocklist_category ON blocklists(category);

-- ── Analytics Snapshots ─────────────────
CREATE TABLE analytics_snapshots (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id              UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    platform            platform_type NOT NULL,
    snapshot_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    views               INTEGER DEFAULT 0,
    likes               INTEGER DEFAULT 0,
    comments            INTEGER DEFAULT 0,
    shares              INTEGER DEFAULT 0,
    watch_time_avg_pct  NUMERIC(5,2),
    raw_data            JSONB,
    CONSTRAINT uq_snapshot UNIQUE (job_id, snapshot_at)
);

CREATE INDEX idx_analytics_job ON analytics_snapshots(job_id);
CREATE INDEX idx_analytics_time ON analytics_snapshots(snapshot_at DESC);

-- ── Updated_at trigger function ─────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_brands_updated_at
    BEFORE UPDATE ON brands FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_jobs_updated_at
    BEFORE UPDATE ON jobs FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_bandit_arms_updated_at
    BEFORE UPDATE ON bandit_arms FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_daily_spend_updated_at
    BEFORE UPDATE ON daily_spend FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_platform_credentials_updated_at
    BEFORE UPDATE ON platform_credentials FOR EACH ROW EXECUTE FUNCTION update_updated_at();
