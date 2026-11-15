"""Build a scene-graph plan."""
from __future__ import annotations

def build_graph(scenes, assets: dict):
    plan = []
    for sc in scenes:
        entry = assets.get(sc.scene_id, {})
        plan.append({
            "scene_id": sc.scene_id,
            "duration": sc.narration.scene_duration_sec,
            "start": sc.timeline.scene_start_sec,
            "end": sc.timeline.scene_end_sec,
            "primary": entry.get("primary"),
            "fallback": entry.get("card"),
            "kinetic": sc.kinetic.events[0].display_text if sc.kinetic.events else "",
            "on_screen": sc.narration.on_screen_text,
            "transition_out": sc.visual_plan.transition_out,
        })
    return plan