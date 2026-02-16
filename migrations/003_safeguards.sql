-- Migration 003: Safeguards & Pivot System

CREATE TYPE pivot_mode AS ENUM ('normal', 'pivot_a', 'pivot_b');

CREATE TABLE IF NOT EXISTS brand_state (
    brand_id VARCHAR(255) PRIMARY KEY,
    pivot_mode pivot_mode DEFAULT 'normal',
    last_pivot_date TIMESTAMP,
    consecutive_failures INT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS weekly_stats (
    id SERIAL PRIMARY KEY,
    brand_id VARCHAR(255) NOT NULL,
    week_start DATE NOT NULL,
    top_5_posts JSONB, -- Check constraints in code
    bottom_5_posts JSONB,
    recommendations JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(brand_id, week_start)
);

-- Add tracking columns to jobs table (assuming it exists from 001)
ALTER TABLE jobs 
ADD COLUMN IF NOT EXISTS hook_archetype VARCHAR(50),
ADD COLUMN IF NOT EXISTS asset_source VARCHAR(50),
ADD COLUMN IF NOT EXISTS cost_usd DECIMAL(10, 4);
