"""
Core data models for the Evidence-driven Video Essay.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any


@dataclass
class WordTs:
    word: str
    start: float
    end: float


@dataclass
class KineticEvent:
    trigger_word: str
    word_index: int
    start_time: float
    end_time: float
    animation_preset: str
    display_text: str
    display_text_source: str
    position: str = "CENTER"
    font: str = "DejaVuSans-Bold.ttf"
    scale: float = 1.0
    color: str = "#FFFFFF"
    background_dimming: float = 0.55
    explanation: str = ""


@dataclass
class KineticBlock:
    eligible: bool = False
    eligibility_reason: str = ""
    events: List[KineticEvent] = field(default_factory=list)


@dataclass
class Narration:
    original_narration: str
    tts_narration: str
    tts_punctuation_only: str = ""
    on_screen_text: str = ""
    word_timestamps: List[WordTs] = field(default_factory=list)
    scene_duration_sec: float = 0.0
    vo_start_sec: float = 0.0
    vo_end_sec: float = 0.0


@dataclass
class Evidence:
    evidence_type: str = "BROLL"
    visual_goal: str = ""
    visual_prompt: str = ""          # Short English prompt for vision matching (CLIP)
    fallback_strategy: str = "EVIDENCE_CARD"
    source_label: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": False, "user_provided": False, "label_text": ""
    })
    search_queries: List[str] = field(default_factory=list)


@dataclass
class VisualPlan:
    """
    Per-scene hybrid visual decision.
    Priority: Pixabay B-roll > specific still (doc/map/chart/diagram) > card.
    """
    visual_mode: str = "BROLL_PRIMARY"          # BROLL_PRIMARY | STILL_PRIMARY | COMPOSITE | FALLBACK_CARD
    primary_visual_type: str = "BROLL"          # BROLL | DOCUMENT | MAP | CHART | DIAGRAM | CARD
    secondary_layers: List[str] = field(default_factory=list)
    # Values: KINETIC_TEXT | LABEL | HIGHLIGHT_SWEEP | CHART | MAP_PIN | DIAGRAM | TIMELINE_CHART
    fallback_visual_type: str = "CARD"
    reason_for_visual_choice: str = ""
    
    # Motion Graphics additions
    motion_hints: List[str] = field(default_factory=list)
    # Values: COUNTER | XFADE | ANIMATED_CHART | LOWER_THIRD | SPLIT_SCREEN
    transition_out: str = "HARD_CUT"  # HARD_CUT | FADE | WIPELEFT | SLIDEUP


@dataclass
class MediaSelection:
    primary_asset: Optional[Dict[str, Any]] = None
    fallback_asset: Optional[Dict[str, Any]] = None
    relevance: Optional[Dict[str, Any]] = None
    source_media: Optional[Dict[str, Any]] = field(default_factory=lambda: {
        "provider": "", "source_url": "", "source_duration_sec": 0.0,
    })
    selected_segment: Optional[Dict[str, Any]] = field(default_factory=lambda: {
        "start_sec": 0.0, "end_sec": 0.0, "duration_sec": 0.0,
        "selection_method": "", "score": 0.0, "score_breakdown": {},
        "confidence_explanation": "", "review_required": False,
    })


@dataclass
class AudioSpec:
    music_level: float = 0.25
    ambience_context: str = "NEUTRAL"
    sfx_trigger: Optional[str] = None
    ducking_active: bool = True


@dataclass
class Technical:
    render_status: str = "PENDING"
    gate_result: Optional[str] = None
    gate_warnings: List[str] = field(default_factory=list)
    review_required: bool = False
    review_reason: Optional[str] = None


@dataclass
class Timeline:
    scene_start_sec: float = 0.0
    scene_end_sec: float = 0.0
    transition_in: str = "HARD_CUT"
    transition_out: str = "HARD_CUT"


@dataclass
class Scene:
    scene_id: int
    job_id: str
    language: str
    chapter: str
    beat_type: str
    narration: Narration
    kinetic: KineticBlock = field(default_factory=KineticBlock)
    evidence: Evidence = field(default_factory=Evidence)
    visual_plan: VisualPlan = field(default_factory=VisualPlan)
    media: MediaSelection = field(default_factory=MediaSelection)
    audio: AudioSpec = field(default_factory=AudioSpec)
    technical: Technical = field(default_factory=Technical)
    timeline: Timeline = field(default_factory=Timeline)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)