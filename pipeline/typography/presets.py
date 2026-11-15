"""Kinetic typography animation presets (describe, not execute)."""
PRESETS = {
    "FADE_UP":          {"in_ms": 280, "out_ms": 200, "easing": "ease_out", "translate_y": 20},
    "FADE_DOWN":        {"in_ms": 280, "out_ms": 200, "easing": "ease_out", "translate_y": -20},
    "WORD_POP":         {"in_ms": 180, "out_ms": 150, "easing": "overshoot", "scale_from": 0.6},
    "PHRASE_SCALE":     {"in_ms": 320, "out_ms": 220, "easing": "ease_in_out", "scale_from": 0.85},
    "NUMBER_ROLL":      {"in_ms": 400, "out_ms": 250, "easing": "linear", "roll": True},
    "TRACKING_REVEAL":  {"in_ms": 380, "out_ms": 200, "letter_spacing_from": -4},
    "MASK_WIPE":        {"in_ms": 340, "out_ms": 220, "mask": "left_to_right"},
    "HIGHLIGHT_SWEEP":  {"in_ms": 260, "out_ms": 220, "highlight": True},
    "SPLIT_REVEAL":     {"in_ms": 300, "out_ms": 200, "split": "halves"},
    "QUOTE_BUILD":      {"in_ms": 380, "out_ms": 200, "build_lines": True},
    "KINETIC_STATEMENT":{"in_ms": 240, "out_ms": 180, "shake": 1.0},
    "DATA_CALLOUT":     {"in_ms": 260, "out_ms": 180, "arrow": True},
    "DOCUMENT_HIGHLIGHT": {"in_ms": 300, "out_ms": 220, "rectangle": True},
    "MAP_CALLOUT":      {"in_ms": 300, "out_ms": 220, "pin": True},
}

def pick_preset(beat_type: str, elements: dict) -> str:
    if beat_type == "STATISTICAL_CLAIM":
        return "DATA_CALLOUT"
    if beat_type == "TIMELINE":
        return "TRACKING_REVEAL"
    if beat_type == "QUOTE":
        return "QUOTE_BUILD"
    if beat_type == "QUESTION":
        return "KINETIC_STATEMENT"
    if beat_type == "PERSON":
        return "WORD_POP"
    if beat_type == "PLACE":
        return "MAP_CALLOUT"
    if beat_type == "CONTRAST":
        return "SPLIT_REVEAL"
    if beat_type == "CONCLUSION":
        return "PHRASE_SCALE"
    if elements.get("numbers"):
        return "NUMBER_ROLL"
    return "FADE_UP"