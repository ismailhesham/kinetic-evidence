"""
Decide the best hybrid visual mix per scene.
"""
from __future__ import annotations
from .schema import VisualPlan
from . import visual_elements

TECHNICAL_KEYWORDS = (
    "how it works", "mechanism", "process", "system", "pipeline",
    "algorithm", "engine", "designed to", "architecture", "circuit",
    "protocol", "procedure", "workflow", "framework", "model",
)

def build_visual_plan(scene) -> VisualPlan:
    beat = scene.beat_type
    text = scene.narration.original_narration.lower()
    elements = visual_elements.extract(scene.narration.original_narration)

    # 1. Technical / process content
    if any(k in text for k in TECHNICAL_KEYWORDS):
        plan = VisualPlan(
            visual_mode="COMPOSITE",
            primary_visual_type="BROLL",
            secondary_layers=["DIAGRAM", "LABEL", "KINETIC_TEXT"],
            fallback_visual_type="DIAGRAM",
            reason_for_visual_choice="Technical/process content.",
            motion_hints=["LOWER_THIRD"],
            transition_out="FADE" if scene.scene_id > 1 else "HARD_CUT"
        )
        return plan

    # 2. Place / location
    if beat == "PLACE" or (elements.get("places") and beat in ("CONTEXT", "INTRODUCTION")):
        plan = VisualPlan(
            visual_mode="COMPOSITE",
            primary_visual_type="BROLL",
            secondary_layers=["MAP_PIN", "KINETIC_TEXT"],
            fallback_visual_type="MAP",
            reason_for_visual_choice="Place-related scene.",
            motion_hints=["LOWER_THIRD"],
            transition_out="FADE" if scene.scene_id > 1 else "HARD_CUT"
        )
        return plan

    # 3. Statistical claim / number
    if beat == "STATISTICAL_CLAIM":
        plan = VisualPlan(
            visual_mode="COMPOSITE",
            primary_visual_type="BROLL",
            secondary_layers=["CHART", "KINETIC_TEXT"],
            fallback_visual_type="CHART",
            reason_for_visual_choice="Numeric claim.",
            motion_hints=["COUNTER", "ANIMATED_CHART"],
            transition_out="FADE" if scene.scene_id > 1 else "HARD_CUT"
        )
        return plan

    # 4. Quote
    if beat == "QUOTE":
        plan = VisualPlan(
            visual_mode="STILL_PRIMARY",
            primary_visual_type="DOCUMENT",
            secondary_layers=["HIGHLIGHT_SWEEP", "KINETIC_TEXT"],
            fallback_visual_type="CARD",
            reason_for_visual_choice="Quoted line.",
            motion_hints=[],
            transition_out="FADE" if scene.scene_id > 1 else "HARD_CUT"
        )
        return plan

    # 5. Timeline
    if beat == "TIMELINE":
        plan = VisualPlan(
            visual_mode="COMPOSITE",
            primary_visual_type="BROLL",
            secondary_layers=["TIMELINE_CHART", "KINETIC_TEXT"],
            fallback_visual_type="CHART",
            reason_for_visual_choice="Temporal sequence.",
            motion_hints=["ANIMATED_CHART"],
            transition_out="FADE" if scene.scene_id > 1 else "HARD_CUT"
        )
        return plan

    # 6. Person
    if beat == "PERSON":
        plan = VisualPlan(
            visual_mode="COMPOSITE",
            primary_visual_type="BROLL",
            secondary_layers=["KINETIC_TEXT"],
            fallback_visual_type="CARD",
            reason_for_visual_choice="Named person.",
            motion_hints=["LOWER_THIRD"],
            transition_out="FADE" if scene.scene_id > 1 else "HARD_CUT"
        )
        return plan

    # 7. Question
    if beat == "QUESTION":
        plan = VisualPlan(
            visual_mode="COMPOSITE",
            primary_visual_type="BROLL",
            secondary_layers=["KINETIC_TEXT"],
            fallback_visual_type="CARD",
            reason_for_visual_choice="Open question.",
            motion_hints=[],
            transition_out="FADE" if scene.scene_id > 1 else "HARD_CUT"
        )
        return plan

    # 8. Contrast / conflict
    if beat in ("CONTRAST", "CONFLICT"):
        plan = VisualPlan(
            visual_mode="COMPOSITE",
            primary_visual_type="BROLL",
            secondary_layers=["LABEL", "KINETIC_TEXT"],
            fallback_visual_type="CARD",
            reason_for_visual_choice="Contrast/conflict.",
            motion_hints=["SPLIT_SCREEN"],
            transition_out="FADE" if scene.scene_id > 1 else "HARD_CUT"
        )
        return plan

    # 9. Introduction / Conclusion
    if beat in ("INTRODUCTION", "CONCLUSION"):
        plan = VisualPlan(
            visual_mode="COMPOSITE",
            primary_visual_type="BROLL",
            secondary_layers=["KINETIC_TEXT"] if elements.get("numbers") or elements.get("names") else [],
            fallback_visual_type="CARD",
            reason_for_visual_choice="Narrative anchor.",
            motion_hints=["LOWER_THIRD"],
            transition_out="FADE" if scene.scene_id > 1 else "HARD_CUT"
        )
        return plan

    # 10. Context / default
    plan = VisualPlan(
        visual_mode="BROLL_PRIMARY",
        primary_visual_type="BROLL",
        secondary_layers=["KINETIC_TEXT"] if elements.get("numbers") else [],
        fallback_visual_type="CARD",
        reason_for_visual_choice="Contextual beat.",
        motion_hints=[],
        transition_out="FADE" if scene.scene_id > 1 else "HARD_CUT"
    )
    return plan