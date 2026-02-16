-- Seed: Default brand profile for testing

INSERT INTO brands (name, palette, font_family, motion_profile, music_bias)
VALUES (
    'Default Brand',
    '["#FF5733", "#1A1A2E", "#EAEAEA", "#16213E"]',
    'Inter',
    'smooth',
    'upbeat'
)
ON CONFLICT (name) DO NOTHING;

-- Seed bandit arms for the default brand
-- Uses a subquery to get the brand_id
INSERT INTO bandit_arms (brand_id, dimension, variant) VALUES
    -- Hook styles
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'hook_style', 'question'),
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'hook_style', 'statistic'),
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'hook_style', 'challenge'),
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'hook_style', 'story'),
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'hook_style', 'controversial'),
    -- Lengths
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'length', '15s'),
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'length', '30s'),
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'length', '45s'),
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'length', '60s'),
    -- Art modes
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'art_mode', 'photorealistic'),
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'art_mode', 'illustration'),
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'art_mode', '3d_render'),
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'art_mode', 'abstract'),
    -- Music styles
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'music_style', 'upbeat'),
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'music_style', 'chill'),
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'music_style', 'dramatic'),
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'music_style', 'none'),
    -- Music styles (new)
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'music_style', 'cinematic'),
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'music_style', 'cinematic_pulse'),
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'music_style', 'modern_minimal'),
    -- Fonts
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'font', 'Inter'),
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'font', 'Montserrat'),
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'font', 'Playfair Display'),
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'font', 'Poppins'),
    ((SELECT id FROM brands WHERE name = 'Default Brand'), 'font', 'Roboto')
ON CONFLICT (brand_id, dimension, variant) DO NOTHING;
