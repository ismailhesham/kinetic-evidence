"""End-to-end render pipeline (CLI)."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path

from . import director, alignment, gate, audit, workspace, voiceover
from .typography import engine as typo
from .media import searcher as media_searcher
from .audio import mixer
from .motion import transitions
from .renderer import scene_compositor
from .media.providers import ai_generated


def _enrich_scene_media(sc, res):
    p = res.get("primary")
    if p:
        sc.media.primary_asset = {"path": p["path"], "provider": p.get("provider")}
        sc.media.relevance = p.get("relevance")
        sc.media.source_media = {
            "provider": p.get("provider"),
            "source_url": p.get("source_url"),
            "source_duration_sec": p.get("source_duration_sec") or 0.0,
        }
        sc.media.selected_segment = {
            "start_sec": p.get("selected_start_sec", 0.0),
            "end_sec": p.get("selected_end_sec", 0.0),
            "duration_sec": p.get("selected_duration_sec", 0.0),
            "selection_method": "metadata_frames_ranking",
            "score": p.get("segment_score") or 0.0,
            "score_breakdown": p.get("segment_score_breakdown") or {},
            "confidence_explanation": p.get("segment_explanation", ""),
            "review_required": p.get("review_required", False),
        }


def run(script_text: str, ws_dir: Path = None, preview: bool = False,
        max_scenes: int = None, speed: float = 1.0, use_llm: bool = True) -> dict:
    
    ws = ws_dir or workspace.new_workspace()
    job_id = ws.name

    # 1. Director (DeepSeek → local validation → local fallback)
    scenes = director.split_into_scenes(script_text, job_id=job_id, use_llm=use_llm)
    if not scenes:
        return {"ok": False, "error": "empty_script"}
    if preview and max_scenes:
        scenes = scenes[:max_scenes]

    # 2. Kinetic typography
    for sc in scenes:
        sc.kinetic = typo.build_kinetic_block(sc)

    # 3. Voiceover + alignment
    voice_files = []
    t_cursor = 0.0
    for sc in scenes:
        vo_path = str(ws / "audio" / f"scene_{sc.scene_id}.wav")
        info = voiceover.synth_scene(sc.narration.tts_narration, vo_path, speed=speed)
        dur = max(info["duration"], 1.0)
        sc.narration.scene_duration_sec = dur
        sc.narration.vo_start_sec = t_cursor
        sc.narration.vo_end_sec = t_cursor + dur
        
        sc.narration.word_timestamps = alignment.align(sc.narration.tts_narration, vo_path, dur)
        
        for ev in sc.kinetic.events:
            if sc.narration.word_timestamps:
                idx = min(ev.word_index, len(sc.narration.word_timestamps) - 1)
                ev.start_time = sc.narration.word_timestamps[idx].start
                ev.end_time = sc.narration.word_timestamps[idx].end + 0.4
                
        voice_files.append(vo_path)
        sc.timeline.scene_start_sec = t_cursor
        sc.timeline.scene_end_sec = t_cursor + dur
        t_cursor += dur

    # 4. Audit (original == tts; display_text ⊂ original)
    aud = audit.audit_scenes(scenes)
    workspace.dump_json(ws / "audit.json", aud)
    if not aud["ok"]:
        return {"ok": False, "error": "audit_failed", "issues": aud["issues"]}

    # 5. Media search (Pixabay primary; Local secondary; AI fallback)
    media_dir = ws / "media"
    media_results = {}
    for sc in scenes:
        res = media_searcher.search_scene(sc, str(media_dir))
        media_results[sc.scene_id] = res
        _enrich_scene_media(sc, res)

    # 6. Compose Scene Clips
    clip_paths = []
    scene_logs = []
    for sc in scenes:
        out_dir = ws / "scenes" / f"scene_{sc.scene_id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_mp4 = str(out_dir / "scene.mp4")
        
        # Gate check
        seg_gate = gate.check_segment(media_results[sc.scene_id].get("primary"), sc.narration.scene_duration_sec)
        if seg_gate["status"] == "FAILED":
            return {"ok": False, "error": f"segment_gate_failed_scene_{sc.scene_id}", "gate": seg_gate}

        log = scene_compositor.compose_scene(sc, media_results[sc.scene_id], ws, out_mp4)
        log["selected_segment"] = {
            "source_duration_sec": media_results[sc.scene_id].get("primary", {}).get("source_duration_sec"),
            "selected_start_sec": media_results[sc.scene_id].get("primary", {}).get("selected_start_sec"),
            "selected_end_sec": media_results[sc.scene_id].get("primary", {}).get("selected_end_sec"),
            "selected_duration_sec": media_results[sc.scene_id].get("primary", {}).get("selected_duration_sec"),
            "selection_method": "metadata_frames_ranking",
            "score": media_results[sc.scene_id].get("primary", {}).get("segment_score"),
            "score_breakdown": media_results[sc.scene_id].get("primary", {}).get("segment_score_breakdown") or {},
            "confidence_explanation": media_results[sc.scene_id].get("primary", {}).get("segment_explanation"),
            "review_required": media_results[sc.scene_id].get("primary", {}).get("review_required", False),
            "vision_backend": media_results[sc.scene_id].get("primary", {}).get("vision_backend"),
            "visual_prompt": media_results[sc.scene_id].get("primary", {}).get("visual_prompt"),
            "generated": media_results[sc.scene_id].get("primary", {}).get("metadata", {}).get("generated", False),
        }
        scene_logs.append(log)
        
        if not log["ok"]:
            return {"ok": False, "error": f"scene_{sc.scene_id}_compose_failed", "log": log}
        clip_paths.append(out_mp4)

    # 7. Audio Mixing
    total_vo = str(ws / "audio" / "voice_full.wav")
    voiceover.concat_wavs(voice_files, total_vo)
    total_dur = sum(sc.narration.scene_duration_sec for sc in scenes)
    
    music = mixer.procedural_music(total_dur, str(ws / "audio" / "music.wav"))
    amb = mixer.procedural_ambience(total_dur, str(ws / "audio" / "ambience.wav"))
    final_audio = str(ws / "audio" / "final_mix.wav")
    mixer.mix_voice_with_bed(total_vo, music, amb, final_audio, music_level=0.25, ambience_level=0.10)

    # 8. Final Render (with transitions)
    final_mp4 = str(ws / "final.mp4")
    from .renderer.gpu import detect_nvenc
    use_gpu = detect_nvenc()
    
    if len(clip_paths) > 1:
        ok = transitions.concat_with_xfade(clip_paths, final_audio, final_mp4, transition="fade", duration=0.4, use_gpu=use_gpu)
    else:
        ok = transitions._mux_single(clip_paths[0], final_audio, final_mp4, use_gpu)
        
    if not ok:
        return {"ok": False, "error": "final_concat_failed"}

    # 9. Reports
    g = gate.check_scene(scenes[0], media_ok=True, audio_ok=True)
    workspace.dump_json(ws / "gate.json", g)
    workspace.dump_json(ws / "scenes.json", [s.to_dict() for s in scenes])
    workspace.dump_json(ws / "media_results.json", media_results)

    hybrid_summary = []
    for sc, log in zip(scenes, scene_logs):
        hybrid_summary.append({
            "scene_id": sc.scene_id,
            "beat": sc.beat_type,
            "visual_mode": sc.visual_plan.visual_mode,
            "primary": sc.visual_plan.primary_visual_type,
            "fallback": sc.visual_plan.fallback_visual_type,
            "base_source": log["base_source"],
            "pixabay_found": bool(sc.media.source_media and sc.media.source_media.get("provider") == "pixabay"),
            "secondary_layers": log["secondary_layers_rendered"],
            "source_media": sc.media.source_media,
            "selected_segment": sc.media.selected_segment,
            "reason": sc.visual_plan.reason_for_visual_choice,
            "warnings": log["warnings"],
        })

    tech_report = {
        "job_id": job_id,
        "scene_count": len(scenes),
        "total_duration_sec": total_dur,
        "llm_used": bool(director.deepseek_client.is_available()),
        "pixabay_used": bool(os.environ.get("PIXABAY_API_KEY")),
        "vision_backend": media_results.get(1, {}).get("primary", {}).get("vision_backend"),
        "ai_generation": {
            "enabled": os.environ.get("ALLOW_AI_IMAGES", "false").lower() == "true",
            "status": ai_generated.vision_status(),
            "scenes_using_ai": [l["scene_id"] for l in scene_logs if l.get("selected_segment", {}).get("generated")],
        },
        "audit": aud,
        "gate": g,
        "scene_logs": scene_logs,
        "hybrid_summary": hybrid_summary,
    }
    workspace.dump_json(ws / "technical_report.json", tech_report)

    return {
        "ok": True,
        "ws": str(ws),
        "output_mp4": final_mp4,
        "total_duration_sec": total_dur,
        "audit": aud, "gate": g,
        "scene_count": len(scenes),
        "hybrid_summary": hybrid_summary,
        "scene_logs": scene_logs,
        "technical_report_path": str(ws / "technical_report.json"),
        "llm_used": tech_report["llm_used"],
        "pixabay_used": tech_report["pixabay_used"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--output", default=None)
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--no-llm", action="store_true")
    args = ap.parse_args()
    
    text = Path(args.script).read_text(encoding="utf-8")
    res = run(text, preview=args.preview, speed=args.speed,
              use_llm=not args.no_llm, max_scenes=2 if args.preview else None)
              
    if res.get("ok") and args.output:
        import shutil
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(res["output_mp4"], args.output)
        res["output_mp4"] = args.output
        
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()