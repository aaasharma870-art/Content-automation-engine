-- Seed: Pre-approved viral hook templates per archetype
-- These are template patterns with {topic} placeholders

-- ── Viral hook templates table seed ──
INSERT INTO viral_hook_templates (archetype, template, category) VALUES
    -- Curiosity hooks
    ('curiosity', 'Most people have no idea that {topic}', 'psychology'),
    ('curiosity', 'Scientists just discovered something terrifying about {topic}', 'science'),
    ('curiosity', 'The real reason {topic} works is disturbing', 'general'),
    ('curiosity', 'Nobody talks about the dark side of {topic}', 'general'),
    ('curiosity', 'What happens when you stop {topic}', 'lifestyle'),
    ('curiosity', 'Your brain does this every time you {topic}', 'psychology'),
    ('curiosity', 'The truth about {topic} that experts hide', 'general'),
    ('curiosity', 'This is what {topic} actually looks like', 'visual'),

    -- Contrarian hooks
    ('contrarian', '{topic} is actually making you worse', 'controversial'),
    ('contrarian', 'Everything you know about {topic} is backwards', 'general'),
    ('contrarian', 'Stop doing {topic} immediately', 'urgent'),
    ('contrarian', 'The biggest lie about {topic}', 'general'),
    ('contrarian', '{topic} is a trap and here is why', 'controversial'),
    ('contrarian', 'Why successful people avoid {topic}', 'success'),

    -- Relatable pain hooks
    ('relatable_pain', 'POV you just realized {topic} was a lie', 'pov'),
    ('relatable_pain', 'When you finally understand {topic}', 'realization'),
    ('relatable_pain', 'That moment when {topic} hits different', 'emotional'),
    ('relatable_pain', 'Nobody warned you about {topic}', 'warning'),
    ('relatable_pain', 'If {topic} keeps you up at night watch this', 'empathy'),
    ('relatable_pain', 'The loneliest part about {topic}', 'emotional'),

    -- Bold claim hooks
    ('bold_claim', 'This will change how you see {topic} forever', 'transformation'),
    ('bold_claim', 'One fact about {topic} that changes everything', 'revelation'),
    ('bold_claim', '{topic} in 30 seconds that took years to learn', 'compressed'),
    ('bold_claim', 'The single most important thing about {topic}', 'authority'),
    ('bold_claim', 'Master {topic} with this one mental shift', 'mindset'),

    -- POV hooks
    ('pov', 'POV you discovered the truth about {topic}', 'pov'),
    ('pov', 'POV you are the only one who sees {topic} clearly', 'pov'),
    ('pov', 'POV your therapist explains {topic} to you', 'pov'),
    ('pov', 'POV you finally stopped pretending about {topic}', 'pov'),
    ('pov', 'Imagine understanding {topic} in 15 seconds', 'pov')
ON CONFLICT (archetype, template) DO NOTHING;
