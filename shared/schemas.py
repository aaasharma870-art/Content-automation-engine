from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime

# ==========================================
# Enums
# ==========================================

class Platform(str, Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"

class ContentType(str, Enum):
    # Core
    QUOTE = "quote"
    FACT = "fact"
    NEWS = "news"
    # Growth (Phase 4)
    # Growth (Phase 4)
    INVISIBLE_RULE = "invisible_rule"
    AXIOM = "axiom"  # New: Cinematic/Viral
    TWO_TYPES = "two_types"
    HARSH_TRUTH = "harsh_truth"
    MICRO_STORY = "micro_story"
    BEFORE_AFTER = "before_after"
    COUNTERINTUITIVE = "counterintuitive"
    SILENT_LESSON = "silent_lesson"
    LIST_COUNTDOWN = "list_countdown"
    QA_POLL = "qa_poll"
    PSYCHOLOGY_FACT = "psychology_fact"
    # Entertaining (Phase 4)
    EXPECTATION_REALITY = "expectation_reality"
    POV = "pov"
    YOU_VS_MIND = "you_vs_mind"
    MINI_DRAMA = "mini_drama"
    BUILT_DIFFERENT = "built_different"
    INTERNAL_MONOLOGUE = "internal_monologue"
    SILENT_VISUAL = "silent_visual"
    PLAYFUL_ROAST = "playful_roast"
    TINY_EXAGGERATION = "tiny_exaggeration"
    RELATABLE_TWIST = "relatable_twist"
    # Phase 8: Cinematic Core
    POETRY_CINEMATIC = "poetry_cinematic"
    PSYCHOLOGY_GRAPHIC = "psychology_graphic"

class VisualFamily(str, Enum):
    NIGHT_CITY = "night_city" # Rain, streetlights, traffic
    EMPTY_GYM = "empty_gym"   # Weights, shadows, focus
    LONE_FIGURE = "lone_figure" # Walking away, silhouettes, nature
    ABSTRACT_DARK = "abstract_dark" # Smoke, ink, particles

class HookArchetype(str, Enum):
    CURIOSITY = "curiosity"
    CONTRARIAN = "contrarian"
    RELATABLE_PAIN = "relatable_pain"
    BOLD_CLAIM = "bold_claim"
    POV = "pov"
    QUESTION = "question"
    TINY_EXAGGERATION = "tiny_exaggeration"
    RELATABLE_TWIST = "relatable_twist"

class ContentMode(str, Enum):
    GRIT = "grit"             # Cinematic training/motivation (Dark, moody)
    PSYCHOLOGY = "psychology" # Educational/Framework (Clean, minimal)
    POETRY = "poetry"         # Lyrical/Rhythmic (Deep, looped)
    SUCCESS = "success"       # Bay of Success style (Neon, Neutral, Business)
    WEALTH = "wealth"         # Book For Wealth style (Serif, Paper, Green/Black)
    AXIOM = "axiom"           # AxiomVisions style (Cinematic, Impact, Viral)
    ASTROLOGY = "astrology"   # Bay of Success style (Neon, Zodiac, Ethereal)
    CINEMA = "cinema"         # Movie Clips + Real Music (AI Curated)

class VideoStructure(str, Enum):
    PUNCH = "punch"   # 18-25s (Agitated, fast)
    ARC = "arc"       # 28-40s (Story, journey)
    ESSAY = "essay"   # 45-60s (Deep dive, 3-part framework)

class PivotMode(str, Enum):
    NORMAL = "normal"
    PIVOT_A = "pivot_a" # Short, High Retention
    PIVOT_B = "pivot_b" # High Energy, Humor

class ArtMode(str, Enum):
    CINEMATIC = "cinematic"  # Moody, photo-realistic
    GRAPHIC = "graphic"      # Abstract, clean lines

class TextTreatment(str, Enum):
    BOLD_SHADOW = "bold_shadow"       # Heavy shadow, high contrast
    CLEAN_GLOW = "clean_glow"         # Soft glow, minimal shadow
    MINIMAL_FLOAT = "minimal_float"   # Light, floating text feel
    HIGH_CONTRAST = "high_contrast"   # Maximum readability
    NEON_SIMPLE = "neon_simple"       # Bay of Success: Neon Yellow on Neutral
    SERIF_PAPER = "serif_paper"       # Book For Wealth: Green/Black Serif on Paper

class CaptionPosition(str, Enum):
    CENTER = "center"                 # Dead center (default, safest)
    CENTER_HIGH = "center_high"       # Upper-center within safe zone
    CENTER_LOW = "center_low"         # Lower-center within safe zone

class MusicStyle(str, Enum):
    CINEMATIC_PULSE = "cinematic_pulse"
    EMOTIONAL_PIANO = "emotional_piano"
    MODERN_MINIMAL = "modern_minimal"

class JobState(str, Enum):
    QUEUED = "queued"
    RESEARCHING = "researching"
    WRITING = "writing"
    AUDITING = "auditing"
    RENDERING = "rendering"
    UPLOADING = "uploading"
    POSTED = "posted"
    DRAFTED = "drafted"
    FAILED = "failed"

class RiskFlag(str, Enum):
    SAFE = "safe"
    LOW = "low"
    HIGH = "high"
    BLOCKED = "blocked"

# ==========================================
# Phase 3 Configuration Models
# ==========================================

class AudioTrack(BaseModel):
    track_id: str
    mood: str 
    bpm: int
    energy: float # 0.0 to 1.0
    platform_fit: List[Platform]
    is_trending: bool = False

class MoatConfig(BaseModel):
    tagline: Optional[str] = None
    sfx_hit_path: Optional[str] = None
    color_accent_hex: Optional[str] = None
    text_treatment: str = "standard" # standard, outlined, bold_shadow

class RssSource(BaseModel):
    url: HttpUrl
    name: str
    trust_score: float = 1.0

class BrandProfile(BaseModel):
    id: str
    name: str
    description: str
    
    # Assets & Style
    font_family: str
    palette_hex: List[str]
    assets_path: str
    moat: MoatConfig
    
    # Posting Logic
    slots_utc: List[str] # ["09:00", "15:00"]
    platform_targets: List[Platform]
    
    # Content Banks
    hashtag_bank: Dict[str, List[str]] # {"tier1": [...], "tier2": [...]}
    rss_sources: List[RssSource] = []
    
    # Rules
    forbidden_words: List[str] = []
    music_bias: Dict[MusicStyle, float] = {
        MusicStyle.CINEMATIC_PULSE: 0.7,
        MusicStyle.EMOTIONAL_PIANO: 0.2,
        MusicStyle.MODERN_MINIMAL: 0.1
    }

class Idea(BaseModel):
    """Raw concept collected from the web"""
    id: str
    source: str # youtube, rss, reddit
    title: str
    snippet: str
    url: str
    topic_tags: List[str]
    engagement_score: float = 0.0 # 0 to 100
    
    # Ranking
    final_rank_score: float = 0.0
    is_selected: bool = False

# ==========================================
# Job & Content Models
# ==========================================

class ScriptAtom(BaseModel):
    """A single segment of the video script"""
    segment_type: str # hook, body, cta
    text: str
    duration_estimate: float
    visual_prompt: Optional[str] = None
    visual_style: Optional[str] = None      # e.g., "dark cinematic"
    visual_query: Optional[str] = None      # e.g., "stormy ocean night"
    overlay_path: Optional[str] = None      # V5.3 Phase 3: Path to pre-rendered transparent overlay

class VideoRenderParams(BaseModel):
    resolution: str = "1080x1920"
    fps: int = 30
    duration_seconds: float
    safe_margins: bool = True
    mobile_first: bool = True            # V5: force mobile-safe caption zones
    template_version: str = "v5.0"

    # Phase 3: Assets
    background_url: Optional[str] = None
    audio_track_id: Optional[str] = None
    music_url: Optional[str] = None         # V7: Direct URL/Path to music file
    audio_start_time: float = 0.0

    # V5: Dynamic styling
    text_treatment: Optional[str] = None        # bold_shadow, clean_glow, etc.
    caption_position: Optional[str] = "center"  # center, center_high, center_low
    
    # V7: Engagement & Quality
    color_grade: Optional[str] = None           # natural_clean, cinematic_dark, warm_vintage
    zoom_style: Optional[str] = None            # subtle_slow, ken_burns, static
    text_animation: Optional[str] = None        # fade_in, typewriter, slide_up
    pacing: Optional[str] = None                # calm, moderate, dynamic
    music_volume: Optional[float] = None        # 0.0-1.0 override

class PublishingMeta(BaseModel):
    title: str
    description: str
    tags: List[str]
    privacy: str = "private"
    schedule_time: Optional[datetime] = None

class AssetSource(str, Enum):
    CACHE = "cache"
    STOCK_VIDEO = "stock_video"
    STOCK_IMAGE = "stock_image"
    DALLE = "dalle"

class JobSpec(BaseModel):
    """The Master Contract for a Content Job"""
    job_id: str
    brand_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Strategy
    content_type: ContentType
    content_mode: Optional[ContentMode] = None # V4 Mode
    video_structure: Optional[VideoStructure] = None # V4 Structure
    hook_archetype: Optional[HookArchetype] = None
    experiment_group: str = "control" # control, variant_A, variant_B
    link_variant: str = "default" # newsletter, affiliate, etc.
    
    # Creative Direction
    script: List[ScriptAtom]
    art_mode: ArtMode
    visual_theme: str
    visual_family: Optional[VisualFamily] = None
    
    # Technical Specs
    render_params: VideoRenderParams
    publishing: Dict[Platform, PublishingMeta]
    metadata: Dict[str, Any] = {} # V4 Metadata Pack
    
    # State & Safety
    state: JobState = JobState.QUEUED
    risk_assessment: Dict[str, Any] = {} # {flag: SAFE, reason: "..."}
    safe_mode: bool = False # If true, use cached assets/simpler render

    class Config:
        use_enum_values = True

class WeeklyStats(BaseModel):
    brand_id: str
    week_start: datetime
    top_5_posts: List[Dict] # [{job_id, views, traits}]
    bottom_5_posts: List[Dict]
    recommendations: List[str]

class BrandState(BaseModel):
    brand_id: str
    pivot_mode: PivotMode = PivotMode.NORMAL
    last_pivot_date: Optional[datetime] = None
    consecutive_failures: int = 0

# ==========================================
# Master Hashtag Banks (V6)
# ==========================================

HASHTAG_BANKS = {
    "axiom": {
        "tier1": ["#motivation", "#discipline", "#mindset", "#success", "#grind"],
        "tier2": ["#focusonyourself", "#nevergiveup", "#keepgoing", "#hardwork", "#beastmode"],
        "tier3": ["#motivationalquotes", "#selfimprovement", "#entrepreneurmindset", "#goggins", "#stoic"],
    },
    "psychology": {
        "tier1": ["#psychology", "#mentalhealth", "#darkpsychology", "#selfawareness", "#healing"],
        "tier2": ["#shadowwork", "#emotionalintelligence", "#anxietyrelief", "#trauma", "#narcissist"],
        "tier3": ["#psychologyfacts", "#therapytiktok", "#attachmentstyle", "#innerchild", "#overthinking"],
    },
    "astrology": {
        "tier1": ["#astrology", "#zodiac", "#manifestation", "#1111", "#universe"],
        "tier2": ["#aries", "#taurus", "#gemini", "#cancer", "#leo", "#virgo"],
        "tier3": ["#libra", "#scorpio", "#sagittarius", "#capricorn", "#aquarius", "#pisces"],
    },
    "grit": {
        "tier1": ["#grit", "#hustle", "#neverquit", "#warrior", "#pain"],
        "tier2": ["#noexcuses", "#riseandgrind", "#mentaltoughness", "#comfort", "#sacrifice"],
        "tier3": ["#davidgoggins", "#andyfrisella", "#joceowillink", "#stoicism", "#spartanmindset"],
    },
    "wealth": {
        "tier1": ["#wealth", "#money", "#investing", "#financialfreedom", "#rich"],
        "tier2": ["#passiveincome", "#sidehustle", "#moneymindset", "#abundance", "#millionaire"],
        "tier3": ["#wealthbuilding", "#financialeducation", "#personalfinance", "#compounding", "#assets"],
    },
    "cinema": {
        "tier1": ["#motivation", "#movieclips", "#mindset", "#nevergiveup", "#speech"],
        "tier2": ["#moviescene", "#motivationalspeech", "#celebrity", "#interview", "#iconic"],
        "tier3": ["#rockybalboa", "#denzelwashington", "#kobebryant", "#discipline", "#grindset"],
    },
}
