-- Phase 3 seed data: content_type bandit arms, visual family arms, hook archetype arms

-- ── Content type bandit arms ──
INSERT INTO bandit_arms (brand_id, dimension, variant)
SELECT b.id, 'content_type', v.variant
FROM brands b
CROSS JOIN (VALUES
    ('quote'),
    ('psychology_fact'),
    ('micro_story'),
    ('poetry_movie_edit'),
    ('pov_poetry'),
    ('expectation_vs_reality')
) AS v(variant)
WHERE b.name = 'Default Brand'
ON CONFLICT (brand_id, dimension, variant) DO NOTHING;

-- ── Visual family bandit arms ──
INSERT INTO bandit_arms (brand_id, dimension, variant)
SELECT b.id, 'visual_family', v.variant
FROM brands b
CROSS JOIN (VALUES
    ('graphic_minimal'),
    ('cinematic_quote'),
    ('artsy_symbolic'),
    ('movie_edit_poetry')
) AS v(variant)
WHERE b.name = 'Default Brand'
ON CONFLICT (brand_id, dimension, variant) DO NOTHING;

-- ── Hook archetype bandit arms ──
INSERT INTO bandit_arms (brand_id, dimension, variant)
SELECT b.id, 'hook_archetype', v.variant
FROM brands b
CROSS JOIN (VALUES
    ('curiosity'),
    ('contrarian'),
    ('relatable_pain'),
    ('bold_claim'),
    ('pov')
) AS v(variant)
WHERE b.name = 'Default Brand'
ON CONFLICT (brand_id, dimension, variant) DO NOTHING;

-- ── Post intent bandit arms ──
INSERT INTO bandit_arms (brand_id, dimension, variant)
SELECT b.id, 'post_intent', v.variant
FROM brands b
CROSS JOIN (VALUES
    ('engage'),
    ('share_first'),
    ('save_first')
) AS v(variant)
WHERE b.name = 'Default Brand'
ON CONFLICT (brand_id, dimension, variant) DO NOTHING;

-- ── Add cinematic_pulse and modern_minimal to music_style ──
INSERT INTO bandit_arms (brand_id, dimension, variant)
SELECT b.id, 'music_style', v.variant
FROM brands b
CROSS JOIN (VALUES
    ('cinematic_pulse'),
    ('modern_minimal')
) AS v(variant)
WHERE b.name = 'Default Brand'
ON CONFLICT (brand_id, dimension, variant) DO NOTHING;
