"""
Kinetic typography eligibility + event generation.
Rules: display_text is ALWAYS a literal substring of original_narration.
"""
from __future__ import annotations
import re
from typing import List
from ..schema import KineticBlock, KineticEvent
from .presets import pick_preset

KINETIC_BEATS = {
    "STATISTICAL_CLAIM", "TIMELINE", "QUOTE", "QUESTION",
    "PERSON", "PLACE", "CONTRAST", "CONCLUSION", "RESULT",
}

WORD_RE = re.compile(r"\S+")

def _word_index_of(narration: str, target: str) -> int:
    """Index of first occurrence of a token in narration."""
    pos = narration.find(target)
    if pos < 0:
        return -1
    return len(narration[:pos].split())

def build_kinetic_block(scene) -> KineticBlock:
    beat = scene.beat_type
    narration = scene.narration.original_narration
    events: List[KineticEvent] = []
    eligible = beat in KINETIC_BEATS
    reason = f"BEAT_{beat}" if eligible else "ORDINARY_NARRATIVE"

    # Even in ordinary narration, allow one kinetic event if a strong number/name exists.
    if not eligible:
        nums = re.findall(r"\b\d+(?:\.\d+)?\b", narration)
        if nums:
            eligible = True
            reason = "STRONG_NUMBER_OVERRIDE"

    if eligible:
        # Choose trigger: longest numeric token, else longest noun-ish token
        trigger = None
        for m in re.finditer(r"\b\d[\d,]*(?:\.\d+)?%?\b", narration):
            if trigger is None or len(m.group(0)) > len(trigger):
                trigger = m.group(0)
        if trigger is None:
            # Use capitalized phrase
            m = re.search(r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*", narration)
            if m:
                trigger = m.group(0)
        if trigger is None:
            # First content word
            words = WORD_RE.findall(narration)
            if words:
                trigger = words[min(3, len(words) - 1)]

        if trigger and trigger in narration:
            wi = _word_index_of(narration, trigger)
            preset = pick_preset(beat, {"numbers": re.findall(r"\d+", narration)})
            events.append(KineticEvent(
                trigger_word=trigger,
                word_index=wi if wi >= 0 else 0,
                start_time=0.0,  # filled by alignment stage
                end_time=0.0,
                animation_preset=preset,
                display_text=trigger,          # literal substring guarantee
                display_text_source="original_narration",
                explanation=f"Auto-selected {preset} for trigger '{trigger}' in beat {beat}.",
            ))

    return KineticBlock(eligible=eligible, eligibility_reason=reason, events=events)