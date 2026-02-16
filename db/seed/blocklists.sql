-- Seed: Initial blocklists

-- Copyright blocklist (popular media franchises / recent titles)
INSERT INTO blocklists (category, term, is_regex) VALUES
    ('copyright', 'Marvel', FALSE),
    ('copyright', 'Disney', FALSE),
    ('copyright', 'Nintendo', FALSE),
    ('copyright', 'Star Wars', FALSE),
    ('copyright', 'Harry Potter', FALSE),
    ('copyright', 'Pokemon', FALSE),
    ('copyright', 'Netflix Original', FALSE),
    ('copyright', 'HBO', FALSE)
ON CONFLICT (category, term) DO NOTHING;

-- Brand safety (profanity + sensitive terms)
INSERT INTO blocklists (category, term, is_regex) VALUES
    ('brand_safety', 'fuck', FALSE),
    ('brand_safety', 'shit', FALSE),
    ('brand_safety', 'damn', FALSE),
    ('brand_safety', 'ass', FALSE),
    ('brand_safety', 'bitch', FALSE),
    ('brand_safety', 'kill yourself', FALSE),
    ('brand_safety', 'suicide method', FALSE),
    ('brand_safety', 'drug dealer', FALSE)
ON CONFLICT (category, term) DO NOTHING;

-- Profanity regex patterns
INSERT INTO blocklists (category, term, is_regex) VALUES
    ('brand_safety', 'f[\*\.\-_]?u[\*\.\-_]?c[\*\.\-_]?k', TRUE),
    ('brand_safety', 's[\*\.\-_]?h[\*\.\-_]?i[\*\.\-_]?t', TRUE)
ON CONFLICT (category, term) DO NOTHING;
