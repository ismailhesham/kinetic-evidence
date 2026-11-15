"""
Audit: strict validation to guarantee the script is NEVER changed.
1. original_narration == tts_narration
2. Kinetic display_text is a literal substring of original_narration
"""
from __future__ import annotations


def audit_scenes(scenes) -> dict:
    issues = []
    for sc in scenes:
        n = sc.narration
        if n.original_narration != n.tts_narration:
            issues.append({"scene_id": sc.scene_id, "type": "narration_mismatch"})
        for ev in sc.kinetic.events:
            if ev.display_text not in n.original_narration:
                issues.append({
                    "scene_id": sc.scene_id,
                    "type": "kinetic_display_not_substring",
                    "display_text": ev.display_text,
                })
    return {"ok": len(issues) == 0, "issues": issues}