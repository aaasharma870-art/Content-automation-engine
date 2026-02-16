-- AI Brain: Phase 3 — Content Types, Hook Archetypes, Asset Tracking, Rotation
-- Migration 003

-- ── Content type enum ─────────────────
CREATE TYPE content_type AS ENUM (
    'quote',
    'psychology_fact',
    'micro_story',
    'poetry_movie_edit',
    'pov_poetry',
    'expectation_vs_reality'
);

-- ── Hook archetype enum ───────────────
CREATE TYPE hook_archetype AS ENUM (
    'curiosity',
    'contrarian',
    'relatable_pain',
    'bold_claim',
    'pov'
);

-- ── Visual family enum ────────────────
CREATE TYPE visual_family AS ENUM (
    'graphic_minimal',
    'cinematic_quote',
    'artsy_symbolic',
    'movie_edit_poetry'
);

-- ── Asset source enum ─────────────────
CREATE TYPE asset_source AS ENUM (
    'cache',
    'stock_video',
    'stock_image',
    'dalle',
    'pexels',
    'pixabay',
    'unsplash'
);

-- ── Expand jobs table with content variation fields ──
ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS content_type content_type,
    ADD COLUMN IF NOT EXISTS hook_archetype hook_archetype,
    ADD COLUMN IF NOT EXISTS visual_family visual_family,
    ADD COLUMN IF NOT EXISTS music_style VARCHAR(50),
    ADD COLUMN IF NOT EXISTS post_intent VARCHAR(30) DEFAULT 'engage',
    -- 'engage', 'share_first', 'save_first'
    ADD COLUMN IF NOT EXISTS hook_word_count INTEGER,
    ADD COLUMN IF NOT EXISTS hook_rewrite_attempts INTEGER DEFAULT 0;

-- ── Asset ledger (track every asset used per job) ──
CREATE TABLE asset_ledger (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    brand_id        UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    asset_source    asset_source NOT NULL,
    provider        VARCHAR(50),
    -- 'dalle', 'pexels', 'pixabay', 'unsplash', 'cache', 'local'
    external_id     VARCHAR(200),
    -- provider's ID for the asset
    query_text      TEXT,
    -- search query used to find this asset
    asset_url       TEXT NOT NULL,
    -- final S3 URL
    original_url    TEXT,
    -- original URL from provider
    license_type    VARCHAR(50),
    -- 'free', 'cc0', 'pexels_license', 'pixabay_license', 'unsplash_license'
    attribution     TEXT,
    -- photographer/creator credit
    content_type_tag VARCHAR(30),
    -- 'image', 'video'
    prompt_hash     VARCHAR(64),
    cost_usd        NUMERIC(10,6) DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_asset_ledger_job ON asset_ledger(job_id);
CREATE INDEX idx_asset_ledger_brand ON asset_ledger(brand_id, created_at DESC);
CREATE INDEX idx_asset_ledger_source ON asset_ledger(asset_source, brand_id);
CREATE INDEX idx_asset_ledger_hash ON asset_ledger(prompt_hash);

-- ── Stock asset cache (downloaded stock assets) ──
CREATE TABLE stock_asset_cache (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider        VARCHAR(50) NOT NULL,
    -- 'pexels', 'pixabay', 'unsplash'
    external_id     VARCHAR(200) NOT NULL,
    query_hash      VARCHAR(64) NOT NULL,
    query_text      TEXT NOT NULL,
    asset_type      VARCHAR(20) NOT NULL,
    -- 'image', 'video'
    s3_url          TEXT NOT NULL,
    original_url    TEXT NOT NULL,
    width           INTEGER,
    height          INTEGER,
    duration_s      NUMERIC(8,2),
    -- for video assets
    license_type    VARCHAR(50) NOT NULL,
    attribution     TEXT,
    tags            TEXT[] DEFAULT '{}',
    relevance_score NUMERIC(5,3),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_stock_cache UNIQUE (provider, external_id)
);

CREATE INDEX idx_stock_cache_query ON stock_asset_cache(query_hash, provider);
CREATE INDEX idx_stock_cache_type ON stock_asset_cache(asset_type, provider);

-- ── Content rotation log (tracks recent posts per brand for rotation rules) ──
CREATE TABLE content_rotation_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id        UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    content_type    content_type NOT NULL,
    hook_archetype  hook_archetype,
    visual_family   visual_family,
    post_intent     VARCHAR(30),
    posted_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rotation_brand ON content_rotation_log(brand_id, posted_at DESC);

-- ── Cliché blocklist seed ─────────────
INSERT INTO blocklists (category, term) VALUES
    ('cliche_hook', 'keep grinding'),
    ('cliche_hook', 'never give up'),
    ('cliche_hook', 'trust the process'),
    ('cliche_hook', 'stay motivated'),
    ('cliche_hook', 'work hard'),
    ('cliche_hook', 'rise and grind'),
    ('cliche_hook', 'hustle harder'),
    ('cliche_hook', 'dream big'),
    ('cliche_hook', 'believe in yourself'),
    ('cliche_hook', 'no pain no gain'),
    ('cliche_hook', 'you got this'),
    ('cliche_hook', 'everything happens for a reason'),
    ('cliche_hook', 'stay focused'),
    ('cliche_hook', 'winners never quit')
ON CONFLICT (category, term) DO NOTHING;

-- ── Triggers ──────────────────────────
-- No trigger needed for asset_ledger or stock_asset_cache (no updated_at)
