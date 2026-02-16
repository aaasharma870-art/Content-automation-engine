-- Phase 6: Master Aesthetic Upgrade
-- Adds new visual family enum values and mined_clips table

-- Add new visual families for V6 templates
ALTER TYPE visual_family ADD VALUE IF NOT EXISTS 'glass_card_axiom';
ALTER TYPE visual_family ADD VALUE IF NOT EXISTS 'highlighter_note';

-- Table for tracking mined YouTube source clips
CREATE TABLE IF NOT EXISTS mined_clips (
    id              BIGSERIAL PRIMARY KEY,
    clip_id         TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    channel         TEXT NOT NULL,
    query           TEXT NOT NULL,
    duration_seconds DOUBLE PRECISION,
    s3_url          TEXT,
    compliance_applied BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mined_clips_query ON mined_clips (query);
CREATE INDEX IF NOT EXISTS idx_mined_clips_created ON mined_clips (created_at DESC);
