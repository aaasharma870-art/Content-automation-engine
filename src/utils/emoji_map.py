"""
emoji_map.py - Lexical Emoji Injection Dictionary
===================================================
Maps high-impact spoken words to Unicode emojis for
kinetic typography injection. Used by the editor module.
"""

import re

# ── Master Emoji Dictionary ─────────────────────
# Keys are lowercase trigger words; values are Unicode emojis
EMOJI_MAP = {
    # Money / Finance
    "money": "💰", "cash": "💵", "dollar": "💲", "dollars": "💲",
    "profit": "📈", "revenue": "💰", "income": "💰", "wealth": "💎",
    "rich": "🤑", "millionaire": "🤑", "billionaire": "🤑",
    "invest": "📊", "investing": "📊", "investment": "📊",
    "stock": "📈", "stocks": "📈", "market": "📊", "crypto": "₿",
    "bitcoin": "₿", "trading": "📉", "trade": "📉",
    "bank": "🏦", "debt": "⚠️", "tax": "🏛️", "taxes": "🏛️",
    "budget": "📋", "savings": "🏦", "retire": "🏖️", "retirement": "🏖️",

    # Growth / Success
    "growth": "📈", "success": "🏆", "win": "🏆", "winning": "🏆",
    "champion": "🏆", "goal": "🎯", "goals": "🎯", "target": "🎯",
    "achievement": "🏅", "hustle": "💪", "grind": "⚡",
    "level": "📶", "upgrade": "⬆️", "scale": "🚀", "scaling": "🚀",

    # Power / Energy
    "fire": "🔥", "hot": "🔥", "lit": "🔥", "burn": "🔥",
    "power": "⚡", "energy": "⚡", "force": "💥", "strong": "💪",
    "strength": "💪", "beast": "🦁", "king": "👑", "queen": "👑",
    "empire": "🏰", "warrior": "⚔️", "legend": "🌟",

    # Mind / Psychology
    "brain": "🧠", "mind": "🧠", "mindset": "🧠", "think": "💭",
    "thinking": "💭", "idea": "💡", "ideas": "💡", "genius": "🧠",
    "smart": "🧠", "strategy": "♟️", "focus": "🎯", "learn": "📚",
    "learning": "📚", "knowledge": "📖", "secret": "🤫",
    "secrets": "🤫", "hack": "🔓", "hacks": "🔓", "psychology": "🧠",

    # Danger / Warning
    "danger": "⚠️", "warning": "⚠️", "risk": "⚠️", "mistake": "❌",
    "mistakes": "❌", "wrong": "❌", "fail": "❌", "failure": "❌",
    "crash": "💥", "scam": "🚨", "fraud": "🚨", "lie": "🤥",
    "lies": "🤥", "trap": "🪤", "problem": "🔴", "crisis": "🚨",

    # Time
    "time": "⏰", "clock": "🕐", "fast": "⚡", "quick": "⚡",
    "slow": "🐢", "today": "📅", "tomorrow": "📅", "year": "📆",
    "years": "📆", "forever": "♾️", "moment": "⏳", "now": "⏰",

    # People / Social
    "people": "👥", "team": "👥", "family": "👨‍👩‍👧‍👦", "friend": "🤝",
    "friends": "🤝", "love": "❤️", "heart": "❤️", "world": "🌍",
    "global": "🌍", "everyone": "👥", "nobody": "🚫",

    # Tech
    "ai": "🤖", "robot": "🤖", "computer": "💻", "code": "👨‍💻",
    "technology": "💻", "tech": "💻", "internet": "🌐", "app": "📱",
    "phone": "📱", "data": "📊", "algorithm": "🔢",

    # Positive Emotion
    "amazing": "🤩", "awesome": "🔥", "incredible": "😱",
    "believe": "✨", "dream": "💫", "dreams": "💫", "hope": "🌈",
    "happy": "😊", "freedom": "🦅", "free": "🆓", "best": "🏆",
    "perfect": "✅", "easy": "😎", "simple": "👌",

    # Numbers / Scale
    "million": "🔢", "billion": "🔢", "thousand": "🔢",
    "hundred": "💯", "percent": "📊", "zero": "0️⃣",
    "number": "🔢", "first": "1️⃣", "one": "☝️",
}


def inject_emojis(text: str) -> str:
    """
    Scan text for trigger words and append matching emojis.

    Args:
        text: Input text string

    Returns:
        Text with emojis injected after trigger words
    """
    words = text.split()
    result = []

    for word in words:
        result.append(word)
        # Strip punctuation for lookup
        clean = re.sub(r'[^\w]', '', word).lower()
        if clean in EMOJI_MAP:
            result.append(EMOJI_MAP[clean])

    return " ".join(result)


def get_emoji_for_word(word: str) -> str | None:
    """Look up a single word in the emoji map. Returns emoji or None."""
    clean = re.sub(r'[^\w]', '', word).lower()
    return EMOJI_MAP.get(clean)
