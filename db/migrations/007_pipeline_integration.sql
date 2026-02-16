-- Phase 7: Pipeline Integration
-- Wires content generation → music search → renderer end-to-end
-- Adds columns to persist edit directives, text overlay, music mood, and attribution

-- ── New columns on jobs table ───────────────
ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS edit_directives   JSONB,
    -- Full edit directives from QuoteEngine (pacing, zoom, color_grade, font, animation, etc.)
    ADD COLUMN IF NOT EXISTS text_lines        TEXT[],
    -- Text overlay lines for the renderer
    ADD COLUMN IF NOT EXISTS beat_timestamps   DOUBLE PRECISION[],
    -- Beat-sync timestamps for line reveals
    ADD COLUMN IF NOT EXISTS attribution       TEXT,
    -- Attribution line e.g. "— Tyler Durden, Fight Club"
    ADD COLUMN IF NOT EXISTS highlight_color   VARCHAR(20),
    -- Highlight color for highlighter_note template ("psych" or "astro")
    ADD COLUMN IF NOT EXISTS music_mood        VARCHAR(50);
    -- Resolved music mood (cinematic_emotional, dark_cinematic, etc.)
