-- Phase 2 seed data: slots, collectors, alerts, expanded bandit arms

-- ── Default publish slots (3 per day per platform) ──
-- YouTube: 12pm, 5pm, 9pm ET
INSERT INTO publish_slots (brand_id, platform, day_of_week, publish_hour, publish_minute, timezone, jitter_minutes)
SELECT b.id, p.platform, d.dow, s.hour, 0, 'America/New_York', 12
FROM brands b
CROSS JOIN (VALUES ('youtube'::platform_type), ('tiktok'::platform_type), ('instagram'::platform_type)) AS p(platform)
CROSS JOIN (VALUES (0),(1),(2),(3),(4),(5),(6)) AS d(dow)
CROSS JOIN (VALUES (12),(17),(21)) AS s(hour)
WHERE b.name = 'Default Brand'
ON CONFLICT (brand_id, platform, day_of_week, publish_hour) DO NOTHING;

-- ── Default collector configs ──
INSERT INTO collector_configs (brand_id, source, config, run_interval_minutes)
SELECT b.id, 'youtube_search'::idea_source,
    '{"keywords": ["viral shorts", "trending topics", "mind blowing facts"], "recency_days": 3, "max_results": 20}'::jsonb,
    360
FROM brands b WHERE b.name = 'Default Brand'
ON CONFLICT (brand_id, source) DO NOTHING;

INSERT INTO collector_configs (brand_id, source, config, run_interval_minutes)
SELECT b.id, 'reddit'::idea_source,
    '{"subreddits": ["todayilearned", "interestingasfuck", "Damnthatsinteresting", "science"], "min_upvotes": 100, "sort": "hot", "time_filter": "day", "max_results": 20}'::jsonb,
    360
FROM brands b WHERE b.name = 'Default Brand'
ON CONFLICT (brand_id, source) DO NOTHING;

INSERT INTO collector_configs (brand_id, source, config, run_interval_minutes)
SELECT b.id, 'rss_feed'::idea_source,
    '{"feeds": [{"url": "https://news.ycombinator.com/rss", "label": "Hacker News"}, {"url": "https://www.reddit.com/r/todayilearned/.rss", "label": "TIL RSS"}]}'::jsonb,
    360
FROM brands b WHERE b.name = 'Default Brand'
ON CONFLICT (brand_id, source) DO NOTHING;

-- ── Default alert rules ──
INSERT INTO alert_rules (name, rule_type, config, webhook_url, cooldown_minutes) VALUES
    ('No post by 10:30am', 'no_post_by_time', '{"check_time": "10:30", "timezone": "America/New_York"}', NULL, 1440),
    ('Budget 90% warning', 'budget_exceeded', '{"threshold_percent": 90}', NULL, 60),
    ('Budget projected overage', 'budget_projected', '{"threshold_percent": 100, "lookahead_hours": 6}', NULL, 120),
    ('Stale job alert', 'stale_job', '{"max_minutes_without_transition": 30}', NULL, 30),
    ('DLQ depth alert', 'dlq_depth', '{"max_unresolved": 3}', NULL, 60)
ON CONFLICT (name) DO NOTHING;

-- ── Expanded bandit arms: layout_variant dimension ──
INSERT INTO bandit_arms (brand_id, dimension, variant)
SELECT b.id, 'layout_variant', v.variant
FROM brands b
CROSS JOIN (VALUES
    ('center_text'),
    ('upper_third'),
    ('lower_third'),
    ('split_screen'),
    ('bold_stroke')
) AS v(variant)
WHERE b.name = 'Default Brand'
ON CONFLICT (brand_id, dimension, variant) DO NOTHING;

-- ── Update default brand with expanded fields ──
UPDATE brands SET
    hashtag_bank = '{
        "youtube": ["#shorts", "#viral", "#fyp", "#mindblown", "#facts"],
        "tiktok": ["#fyp", "#viral", "#learnontiktok"],
        "instagram": ["#reels", "#viral", "#explore", "#trending"]
    }'::jsonb,
    topic_keywords = ARRAY['science', 'psychology', 'history', 'technology', 'nature', 'space'],
    posting_cadence = '{"youtube": {"max_per_day": 2}, "tiktok": {"max_per_day": 3}, "instagram": {"max_per_day": 2}}'::jsonb,
    font_variants = '{"heading": "Inter-Bold", "body": "Inter-Regular", "accent": "Montserrat-Bold"}'::jsonb,
    safe_margins = '{"youtube": {"top_px": 120, "bottom_px": 160, "left_px": 40, "right_px": 40}, "tiktok": {"top_px": 200, "bottom_px": 180, "left_px": 40, "right_px": 40}, "instagram": {"top_px": 160, "bottom_px": 160, "left_px": 40, "right_px": 40}}'::jsonb,
    timezone = 'America/New_York'
WHERE name = 'Default Brand';
