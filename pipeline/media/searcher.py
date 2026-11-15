"""
Media search + segment selection orchestrator.
"""
from __future__ import annotations
import os
import shutil
from pathlib import Path
from . import cache, evaluator, segment_selector
from .downloader import download_many
from .providers import (local, pixabay, wikimedia_commons,
                        internet_archive, nasa, press_kit,
                        official_safety, ai_generated)

VIDEO_PROVIDERS = [pixabay, wikimedia_commons, internet_archive, nasa, local]
DISCOVERY_PROVIDERS = [press_kit, official_safety]

def build_queries(scene) -> list:
    qs = [q for q in (scene.evidence.search_queries or [])
          if isinstance(q, str) and q.strip()]
    if qs:
        return qs
    goal = (scene.evidence.visual_goal or "documentary b-roll").rstrip(".")
    goal = goal.replace("Show ", "").replace("the script", "narrative")
    return [goal] if goal else ["documentary context"]

def _ai_fallback(scene, out_dir: Path):
    if os.environ.get("ALLOW_AI_IMAGES", "false").strip().lower() not in ("true", "1", "yes", "on"):
        return None
    prompt = (scene.evidence.visual_prompt or scene.evidence.visual_goal or scene.narration.original_narration[:200])
    ai_out = out_dir / f"scene_{scene.scene_id}" / "ai"
    hits = ai_generated.generate(prompt, str(ai_out), width=1280, height=720)
    if not hits:
        return None
    h = hits[0]
    return {
        "path": h["path"], "provider": "ai_generated", "source_path": h["path"],
        "source_url": None, "source_duration_sec": None, "selected_start_sec": 0.0,
        "selected_end_sec": None, "selected_duration_sec": None, "segment_score": None,
        "segment_score_breakdown": {}, "segment_explanation": "ai_generated_illustration",
        "review_required": True, "vision_backend": None, "visual_prompt": prompt,
        "metadata": h["metadata"], "relevance": {"composite_score": 0.5, "confidence_explanation": "ai_generated_as_last_resort", "review_required": True},
    }

def _search_providers(queries, kind, warnings):
    all_hits = []
    for q in queries:
        cached = cache.lookup("*", q, kind)
        if cached:
            all_hits.append({"provider": "cache", "path": cached["path"], "metadata": cached.get("meta", {})})
            continue
        for p in VIDEO_PROVIDERS:
            try:
                for h in p.search(q, kind=kind):
                    if h.get("metadata", {}).get("kind") == "discovery":
                        continue
                    all_hits.append(h)
            except Exception as e:
                warnings.append(f"provider_{p.__name__}_error: {e}")
    return all_hits

def _evaluate_hits(all_hits, queries):
    if not all_hits:
        return None
    best = None
    for h in all_hits:
        rel = evaluator.evaluate(" ".join(queries), h, negative_keywords=["nsfw", "logo", "watermark"], shot_type_needed=h.get("metadata", {}).get("kind", "video"))
        h["relevance"] = rel
        if best is None or rel["composite_score"] > best["relevance"]["composite_score"]:
            best = h
    return best

def search_scene(scene, out_dir: str, kind: str = "video") -> dict:
    queries = build_queries(scene)
    scene_dur = float(getattr(scene.narration, "scene_duration_sec", 5.0) or 5.0)
    warnings = []
    discovery_results = []

    for p in DISCOVERY_PROVIDERS:
        for q in queries:
            try:
                discovery_results.extend(p.search(q, kind=kind))
            except Exception:
                pass

    all_hits = _search_providers(queries, "video", warnings)
    best = _evaluate_hits(all_hits, queries)

    if not best:
        warnings.append("no_video_found_searching_images")
        all_hits = _search_providers(queries, "image", warnings)
        best = _evaluate_hits(all_hits, queries)

    if not best:
        ai_primary = _ai_fallback(scene, Path(out_dir))
        if ai_primary:
            return {"primary": ai_primary, "relevance": ai_primary["relevance"], "queries": queries, "warnings": warnings + ["using_ai_generated_illustration"], "discovery": discovery_results}
        return {"primary": None, "relevance": None, "queries": queries, "warnings": warnings + ["no_media_found"], "discovery": discovery_results}

    primary = None
    if best.get("path"):
        primary = {"path": best["path"], "provider": best.get("provider"), "relevance": best["relevance"],
                   "source_path": best["path"], "source_url": None, "source_duration_sec": None,
                   "selected_start_sec": 0.0, "selected_end_sec": None, "selected_duration_sec": None,
                   "segment_score": None, "segment_score_breakdown": {}, "segment_explanation": "local_asset_no_segmentation",
                   "review_required": False, "vision_backend": None, "visual_prompt": "", "metadata": best.get("metadata", {})}

    elif best.get("url"):
        dl_dir = Path(out_dir) / f"scene_{scene.scene_id}"
        dl_dir.mkdir(parents=True, exist_ok=True)
        
        is_video = best.get("metadata", {}).get("kind") == "video"
        ext = ".mp4" if is_video else ".jpg"
        source = dl_dir / f"source{ext}"
        
        res = download_many([{"url": best["url"], "out_path": str(source)}], str(dl_dir))
        if not (res and res[0]["ok"] and source.exists() and source.stat().st_size > 1024):
            warnings.append("download_failed")
            ai_primary = _ai_fallback(scene, Path(out_dir))
            if ai_primary:
                return {"primary": ai_primary, "relevance": ai_primary["relevance"], "queries": queries, "warnings": warnings + ["using_ai_generated_illustration"], "discovery": discovery_results}
            return {"primary": None, "relevance": best["relevance"], "queries": queries, "warnings": warnings, "discovery": discovery_results}

        if is_video:
            seg = segment_selector.select_segment(str(source), scene.narration.original_narration, scene.evidence.visual_goal, queries, scene_dur, best.get("metadata", {}), persist_frames_to=str(dl_dir / "frames"), visual_prompt=scene.evidence.visual_prompt)
            if not seg["ok"]:
                warnings.append("segment_selection_failed")
                ai_primary = _ai_fallback(scene, Path(out_dir))
                if ai_primary:
                    return {"primary": ai_primary, "relevance": ai_primary["relevance"], "queries": queries, "warnings": warnings + ["using_ai_generated_illustration"], "discovery": discovery_results}
                return {"primary": None, "relevance": best["relevance"], "queries": queries, "warnings": warnings, "discovery": discovery_results}

            selected = dl_dir / "selected_clip.mp4"
            ok = segment_selector.trim_video_segment(str(source), str(selected), seg["selected_start_sec"], seg["selected_duration_sec"], scene_dur)
            if not ok:
                warnings.append("segment_trim_failed")
                ai_primary = _ai_fallback(scene, Path(out_dir))
                if ai_primary:
                    return {"primary": ai_primary, "relevance": ai_primary["relevance"], "queries": queries, "warnings": warnings + ["using_ai_generated_illustration"], "discovery": discovery_results}
                return {"primary": None, "relevance": best["relevance"], "queries": queries, "warnings": warnings, "discovery": discovery_results}

            try:
                if source.exists(): source.unlink()
                frames_dir = dl_dir / "frames"
                if frames_dir.exists(): shutil.rmtree(frames_dir)
            except Exception as e:
                warnings.append(f"cleanup_failed: {e}")

            primary = {
                "path": str(selected), "provider": best.get("provider"), "source_path": str(source),
                "source_url": best.get("url"), "source_duration_sec": seg["source_duration_sec"],
                "selected_start_sec": seg["selected_start_sec"], "selected_end_sec": seg["selected_end_sec"],
                "selected_duration_sec": seg["selected_duration_sec"], "segment_score": seg["score"],
                "segment_score_breakdown": seg["score_breakdown"], "segment_explanation": seg["confidence_explanation"],
                "review_required": seg["review_required"], "vision_backend": seg.get("vision_backend"),
                "visual_prompt": seg.get("visual_prompt", ""), "metadata": best.get("metadata", {}),
                "relevance": best["relevance"],
            }
        else:
            primary = {
                "path": str(source), "provider": best.get("provider"), "source_path": str(source),
                "source_url": best.get("url"), "source_duration_sec": None,
                "selected_start_sec": 0.0, "selected_end_sec": None, "selected_duration_sec": None,
                "segment_score": best["relevance"].get("composite_score"), "segment_score_breakdown": {},
                "segment_explanation": "static_image_selected", "review_required": False,
                "vision_backend": None, "visual_prompt": "", "metadata": best.get("metadata", {}),
                "relevance": best["relevance"],
            }

    return {"primary": primary, "relevance": best["relevance"], "queries": queries, "warnings": warnings, "discovery": discovery_results}
