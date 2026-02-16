-- AI Brain: Phase 5 — Viral Hook Templates, Quality Scoring, Music Tracking
-- Migration 005

-- ── Viral hook templates ────────────────
CREATE TABLE IF NOT EXISTS viral_hook_templates (
    id              SERIAL PRIMARY KEY,
    archetype       VARCHAR(50) NOT NULL,
    template        TEXT NOT NULL,
    category        VARCHAR(50) NOT NULL DEFAULT 'general',
    times_used      INTEGER NOT NULL DEFAULT 0,
    avg_hold_rate   NUMERIC(5,3),
    avg_shares      NUMERIC(8,6),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_hook_template UNIQUE (archetype, template)
);

CREATE INDEX idx_hook_templates_archetype ON viral_hook_templates(archetype) WHERE is_active = TRUE;

-- ── Track music source on jobs ──────────
ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS music_url TEXT,
    ADD COLUMN IF NOT EXISTS music_provider VARCHAR(50),
    ADD COLUMN IF NOT EXISTS font_used VARCHAR(100);

-- ── Expand bandit dimensions for font selection ──
-- (font arms already seeded in brand_defaults.sql, but add Playfair Display)
INSERT INTO bandit_arms (brand_id, dimension, variant)
SELECT b.id, 'font', v.variant
FROM brands b
CROSS JOIN (VALUES
    ('Playfair Display')
) AS v(variant)
WHERE b.name = 'Default Brand'
ON CONFLICT (brand_id, dimension, variant) DO NOTHING;

-- ── Add music_style arms for new moods ──
INSERT INTO bandit_arms (brand_id, dimension, variant)
SELECT b.id, 'music_style', v.variant
FROM brands b
CROSS JOIN (VALUES
    ('chill'),
    ('cinematic')
) AS v(variant)
WHERE b.name = 'Default Brand'
ON CONFLICT (brand_id, dimension, variant) DO NOTHING;
