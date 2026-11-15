"""End-to-end render pipeline (CLI)."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from . import director, alignment, gate, audit, workspace, voiceover
from .typography import engine as typo
from .media import searcher as media_searcher
from .audio import mixer
from .motion import transitions
from .renderer import scene_compositor
from .media.providers import ai_generated

load_dotenv()

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
        max_scenes: int = None, speed: float = 1.0, use_llm: bool = True,
        progress_callback=None) -> dict:
    
    def update_progress(pct, msg):
        if progress_callback:
            progress_callback(round(pct, 2), msg)

    ws = ws_dir or workspace.new_workspace()
    job_id = ws.name

    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        BarColumn(), TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
        TimeElapsedColumn(),
    ) as progress:
        
        task = progress.add_task("[cyan]Initializing Pipeline...", total=100)
        
        def cli_update(pct, msg):
            progress.update(task, completed=pct, description=f"[cyan]{msg}")
            update_progress(pct, msg)

        cli_update(1.00, "Analyzing script & segmenting scenes...")
        scenes = director.split_into_scenes(script_text, job_id=job_id, use_llm=use_llm)
        if not scenes:
            return {"ok": False, "error": "empty_script"}
        if preview and max_scenes:
            scenes = scenes[:max_scenes]

        for sc in scenes:
            sc.kinetic = typo.build_kinetic_block(sc)

        voice_files = []
        t_cursor = 0.0
        total_scenes = len(scenes)
        for i, sc in enumerate(scenes):
            pct = 6.0 + ((i / total_scenes) * 14.0)
            cli_update(pct, f"Generating Voiceover for scene {i+1}/{total_scenes}...")
            
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

        cli_update(20.00, "Validating script integrity...")
        aud = audit.audit_scenes(scenes)
        workspace.dump_json(ws / "audit.json", aud)
        if not aud["ok"]:
            return {"ok": False, "error": "audit_failed", "issues": aud["issues"]}

        media_dir = ws / "media"
        media_results = {}
        for i, sc in enumerate(scenes):
            pct = 21.0 + ((i / total_scenes) * 29.0)
            cli_update(pct, f"Searching & downloading media for scene {i+1}/{total_scenes}...")
            
            res = media_searcher.search_scene(sc, str(media_dir))
            media_results[sc.scene_id] = res
            _enrich_scene_media(sc, res)

        clip_paths = []
        scene_logs = []
        for i, sc in enumerate(scenes):
            pct = 50.0 + ((i / total_scenes) * 35.0)
            cli_update(pct, f"Rendering scene visuals (Compositing) {i+1}/{total_scenes}...")
            
            out_dir = ws / "scenes" / f"scene_{sc.scene_id}"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_mp4 = str(out_dir / "scene.mp4")
            
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

        cli_update(85.00, "Mixing Audio & Music...")
        total_vo = str(ws / "audio" / "voice_full.wav")
        voiceover.concat_wavs(voice_files, total_vo)
        total_dur = sum(sc.narration.scene_duration_sec for sc in scenes)
        
        music = mixer.procedural_music(total_dur, str(ws / "audio" / "music.wav"))
        amb = mixer.procedural_ambience(total_dur, str(ws / "audio" / "ambience.wav"))
        final_audio = str(ws / "audio" / "final_mix.wav")
        mixer.mix_voice_with_bed(total_vo, music, amb, final_audio, music_level=0.25, ambience_level=0.10)

        cli_update(90.00, "Finalizing video (FFmpeg Render)...")
        final_mp4 = str(ws / "final.mp4")
        from .renderer.gpu import detect_nvenc
        use_gpu = detect_nvenc()
        
        if len(clip_paths) > 1:
            ok = transitions.concat_with_xfade(clip_paths, final_audio, final_mp4, transition="fade", duration=0.4, use_gpu=use_gpu)
        else:
            ok = transitions._mux_single(clip_paths[0], final_audio, final_mp4, use_gpu)
            
        if not ok:
            return {"ok": False, "error": "final_concat_failed"}

        cli_update(100.00, "Done!")

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
            "job_id": job_id, "scene_count": len(scenes), "total_duration_sec": total_dur,
            "llm_used": bool(director.deepseek_client.is_available()),
            "pixabay_used": bool(os.environ.get("PIXABAY_API_KEY")),
            "vision_backend": media_results.get(1, {}).get("primary", {}).get("vision_backend"),
            "ai_generation": {
                "enabled": os.environ.get("ALLOW_AI_IMAGES", "false").lower() == "true",
                "status": ai_generated.vision_status(),
                "scenes_using_ai": [l["scene_id"] for l in scene_logs if l.get("selected_segment", {}).get("generated")],
            },
            "audit": aud, "gate": g, "scene_logs": scene_logs, "hybrid_summary": hybrid_summary,
        }
        workspace.dump_json(ws / "technical_report.json", tech_report)

        return {
            "ok": True, "ws": str(ws), "output_mp4": final_mp4, "total_duration_sec": total_dur,
            "audit": aud, "gate": g, "scene_count": len(scenes), "hybrid_summary": hybrid_summary,
            "scene_logs": scene_logs, "technical_report_path": str(ws / "technical_report.json"),
            "llm_used": tech_report["llm_used"], "pixabay_used": tech_report["pixabay_used"],
        }
