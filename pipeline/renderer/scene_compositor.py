"""The heavy lifter: composes FFmpeg filters for a single scene."""
from __future__ import annotations
import os
from pathlib import Path
from typing import List, Dict, Optional

from ..generators import cards, charts, documents, maps, diagrams
from ..motion import counters, lower_thirds, text_animations
from ..media import screenshot_capture
from .ffmpeg_runner import run_ffmpeg

W, H = 1280, 720
FPS = 30

IMAGE_LAYERS = {"CHART", "MAP_PIN", "DIAGRAM", "TIMELINE_CHART"}
STILL_TYPES = {"DOCUMENT", "MAP", "CHART", "DIAGRAM"}

def _is_video(p: str) -> bool:
    return p.lower().endswith((".mp4", ".mov", ".webm", ".mkv", ".m4v"))

def _generate_still(vtype: str, scene, ws: Path) -> Optional[str]:
    vtype = (vtype or "").upper()
    if vtype not in STILL_TYPES:
        return None
    out = ws / "scenes" / f"scene_{scene.scene_id}" / "assets"
    out.mkdir(parents=True, exist_ok=True)
    try:
        if vtype == "DOCUMENT":
            p = str(out / "doc.png")
            documents.render_document(scene.narration.original_narration, p)
            return p
        if vtype == "MAP":
            p = str(out / "map.png")
            maps.render_map(scene.narration.original_narration[:40], p)
            return p
        if vtype == "CHART":
            p = str(out / "chart.png")
            return p if charts.render_chart(scene.narration.original_narration, p).get("ok") else None
        if vtype == "DIAGRAM":
            p = str(out / "diagram.png")
            diagrams.render_diagram(scene.narration.original_narration, p)
            return p
    except Exception:
        return None
    return None

def _generate_overlay(layer: str, scene, ws: Path) -> Optional[str]:
    layer = (layer or "").upper()
    out = ws / "scenes" / f"scene_{scene.scene_id}" / "layers"
    out.mkdir(parents=True, exist_ok=True)
    try:
        if layer == "CHART":
            p = str(out / "chart_ov.png")
            return p if charts.render_chart(scene.narration.original_narration, p, w=420, h=236).get("ok") else None
        if layer == "MAP_PIN":
            p = str(out / "map_ov.png")
            maps.render_map(scene.narration.original_narration[:30], p, w=420, h=236)
            return p
        if layer == "DIAGRAM":
            p = str(out / "diagram_ov.png")
            diagrams.render_diagram(scene.narration.original_narration, p, w=420, h=236)
            return p
        if layer == "TIMELINE_CHART":
            p = str(out / "timeline_ov.png")
            return p if charts.render_chart(scene.narration.original_narration, p, w=420, h=236).get("ok") else None
    except Exception:
        return None
    return None


def compose_scene(scene, media_result: Dict, ws: Path, out_mp4: str) -> Dict:
    """
    Builds the FFmpeg command for a scene.
    Returns log dict with base_source, etc.
    """
    dur = scene.narration.scene_duration_sec
    plan = scene.visual_plan
    kinetic = scene.kinetic.events[0] if scene.kinetic.events else None
    
    log = {
        "scene_id": scene.scene_id,
        "base_source": None,
        "secondary_layers_rendered": [],
        "warnings": [],
        "ok": False
    }

    # 1. Determine Base Layer
    primary_media = media_result.get("primary") or {}
    base_path = None
    is_video = False

    if primary_media.get("path"):
        base_path = primary_media["path"]
        is_video = _is_video(base_path)
        log["base_source"] = f"{primary_media.get('provider')}_video" if is_video else f"{primary_media.get('provider')}_image"
    else:
        # Generate fallback based on VisualPlan
        fallback_vtype = plan.fallback_visual_type
        if fallback_vtype in STILL_TYPES:
            base_path = _generate_still(fallback_vtype, scene, ws)
            if base_path:
                log["base_source"] = f"fallback_{fallback_vtype.lower()}"
        if not base_path:
            # Absolute fallback: Evidence Card
            out_dir = ws / "scenes" / f"scene_{scene.scene_id}"
            out_dir.mkdir(parents=True, exist_ok=True)
            base_path = str(out_dir / "card.png")
            cards.render_card(scene.narration.original_narration[:140], base_path, label=scene.beat_type)
            log["base_source"] = "card_last_resort"

    # 2. Build FFmpeg Command
    inputs = []
    if is_video:
        inputs.extend(["-stream_loop", "-1", "-i", base_path])
    else:
        inputs.extend(["-loop", "1", "-i", base_path])
        
    filters = []
    if is_video:
        filters.append(f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},trim=duration={dur:.3f}[base]")
    else:
        nframes = max(int(dur * FPS), FPS)
        filters.append(f"[0:v]scale=iw*1.06:ih*1.06,zoompan=z='min(zoom+0.0006,1.10)':d={nframes}:s={W}x{H}:fps={FPS},setsar=1,trim=duration={dur:.3f}[base]")

    current = "base"
    input_idx = 1
    overlay_slot = 0

    # 3. Add Overlays (Secondary Layers)
    for layer in plan.secondary_layers:
        if layer not in IMAGE_LAYERS:
            continue
        img = _generate_overlay(layer, scene, ws)
        if img and Path(img).exists():
            inputs.extend(["-loop", "1", "-i", img])
            filters.append(f"[{input_idx}:v]scale=420:-1,setsar=1[ov{input_idx}]")
            xy = "W-w-40:H-h-40" if overlay_slot == 0 else "W-w-40:40"
            filters.append(f"[{current}][ov{input_idx}]overlay={xy}:shortest=1[v{input_idx}]")
            current = f"v{input_idx}"
            input_idx += 1
            overlay_slot += 1
            log["secondary_layers_rendered"].append(layer)

    # 4. Add HIGHLIGHT_SWEEP (Box behind text)
    if kinetic and "HIGHLIGHT_SWEEP" in plan.secondary_layers:
        filters.append(f"[{current}]drawbox=x=(w-720)/2:y=(h-120)/2:w=720:h=120:color=0x4f9dff@0.35:t=fill:enable='between(t,{kinetic.start_time:.2f},{kinetic.end_time:.2f})'[{current}h]")
        current = f"{current}h"

    # 5. Add LABEL (Top left)
    if "LABEL" in plan.secondary_layers:
        label_txt = scene.beat_type.replace("_", " ")
        font = text_animations._find_font(bold=False)
        filters.append(f"[{current}]drawtext=text='{label_txt}':fontfile={font}:fontsize=24:fontcolor=0x8fb3ff:x=40:y=40:box=1:boxcolor=black@0.55:boxborderw=10[v{input_idx}]")
        current = f"v{input_idx}"
        input_idx += 1
        log["secondary_layers_rendered"].append("LABEL")

    # 6. Add MOTION GRAPHICS & KINETIC TEXT
    if kinetic:
        # Check if we should use a counter
        use_counter = "COUNTER" in (plan.motion_hints or [])
        counter_filter = counters.build_counter_for_scene(scene, start_time=kinetic.start_time, duration=1.5) if use_counter else None
        
        if counter_filter:
            filters.append(f"[{current}]{counter_filter}[v{input_idx}]")
            current = f"v{input_idx}"
            input_idx += 1
            log["secondary_layers_rendered"].append("COUNTER")
        else:
            # Use normal text animation
            txt_filter = text_animations.build_kinetic_text(kinetic.display_text, kinetic.animation_preset, kinetic.start_time, kinetic.end_time)
            filters.append(f"[{current}]{txt_filter}[v{input_idx}]")
            current = f"v{input_idx}"
            input_idx += 1
            log["secondary_layers_rendered"].append("KINETIC_TEXT")

    # 7. Lower Third (if requested)
    if "LOWER_THIRD" in (plan.motion_hints or []):
        lt_text = scene.evidence.source_label.get("label_text") or scene.chapter
        lt_filter = lower_thirds.build_lower_third(lt_text)
        if lt_filter:
            filters.append(f"[{current}]{lt_filter}[v{input_idx}]")
            current = f"v{input_idx}"
            input_idx += 1
            log["secondary_layers_rendered"].append("LOWER_THIRD")

    # 8. AI Watermark (Mandatory)
    if primary_media.get("metadata", {}).get("generated"):
        font = text_animations._find_font(bold=False)
        filters.append(f"[{current}]drawtext=text='AI ILLUSTRATION':fontfile={font}:fontsize=22:fontcolor=white@0.85:x=w-text_w-28:y=h-46:box=1:boxcolor=black@0.6:boxborderw=10[v{input_idx}]")
        current = f"v{input_idx}"
        input_idx += 1
        log["secondary_layers_rendered"].append("AI_WATERMARK")

    # 9. Source Credit for Screenshots
    if primary_media.get("metadata", {}).get("license_type") == "fair_use_editorial":
        url = primary_media.get("metadata", {}).get("url", "")
        credit = f"Source: {screenshot_capture.domain_credit(url)}"
        cr_filter = lower_thirds.build_lower_third(credit, start_time=0.2, hold=dur-0.4)
        if cr_filter:
            filters.append(f"[{current}]{cr_filter}[v{input_idx}]")
            current = f"v{input_idx}"
            input_idx += 1
            log["secondary_layers_rendered"].append("SOURCE_CREDIT")

    # 10. Finalize Command
    filter_complex = ";".join(filters)
    cmd = ["ffmpeg", "-y", *inputs, "-t", f"{dur:.3f}",
           "-filter_complex", filter_complex, "-map", f"[{current}]", "-an",
           "-c:v", "libx264", "-preset", "fast", "-crf", "22",
           "-pix_fmt", "yuv420p", out_mp4]
           
    log["ok"] = run_ffmpeg(cmd, timeout=600)
    return log