"""Technical Render Gate — only technical issues can stop the render."""
from __future__ import annotations
import shutil
from pathlib import Path

def check_scene(scene, media_ok: bool, audio_ok: bool) -> dict:
    warnings = []
    fatal = []

    if not media_ok and not scene.media.fallback_asset:
        warnings.append(f"scene_{scene.scene_id}:no_primary_media_using_fallback")
    if not audio_ok:
        fatal.append(f"scene_{scene.scene_id}:empty_or_zero_audio")

    disk = shutil.disk_usage(".")
    if disk.free < 500 * 1024 * 1024:  # أقل من 500 ميجا
        fatal.append("insufficient_disk_space")

    if not shutil.which("ffmpeg"):
        fatal.append("ffmpeg_missing")

    status = "FAILED" if fatal else ("PASSED_WITH_WARNINGS" if warnings else "PASSED")
    return {"status": status, "warnings": warnings, "fatal": fatal}

def check_segment(primary: dict, scene_duration: float, tolerance: float = 0.5) -> dict:
    warnings, fatal = [], []
    if not primary:
        return {"status": "SKIPPED", "warnings": ["no_primary"], "fatal": []}

    start = primary.get("selected_start_sec") or 0.0
    end = primary.get("selected_end_sec") or 0.0
    dur = primary.get("selected_duration_sec") or 0.0
    src = primary.get("source_duration_sec") or 0.0
    score = primary.get("segment_score") or 0.0
    path = primary.get("path")

    if start < 0:
        fatal.append("selected_start_negative")
    if end <= start:
        fatal.append("selected_end_not_after_start")
    if src > 0 and end > src + tolerance:
        fatal.append("selected_end_exceeds_source")
    if scene_duration > 0 and dur > scene_duration + tolerance:
        fatal.append("selected_duration_exceeds_scene")
    if not path or not Path(path).exists():
        fatal.append("selected_clip_missing")
    elif primary.get("source_path") and str(path) == str(primary["source_path"]):
        fatal.append("renderer_using_source_video_not_clip")
    if score and score < 0.45:
        warnings.append(f"low_segment_score:{score}")

    status = ("FAILED" if fatal else "PASSED_WITH_WARNINGS" if warnings else "PASSED")
    return {"status": status, "warnings": warnings, "fatal": fatal}