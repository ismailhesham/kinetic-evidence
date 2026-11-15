"""
Select the best short window from a video for a scene.
"""
from __future__ import annotations
import os
import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

MIN_CLIP_DURATION = 3.0
MAX_CLIP_DURATION = 8.0
WINDOW_STEP_SECONDS = 1.0
FRAME_SAMPLE_INTERVAL = 1.0
SCORE_THRESHOLD = 0.45

DEFAULT_CLIP_MODEL = "openai/clip-vit-base-patch32"
DEFAULT_SIGLIP_MODEL = "google/siglip-base-patch16-224"

NEGATIVE_KEYWORDS = {"nsfw", "logo", "watermark", "gore", "explicit",
                     "advertisement", "violence"}
STOP = {"the","a","an","and","or","but","of","to","in","on","at","for",
        "with","by","from","that","this","these","those","is","are","was",
        "were","be","been","being","it","its","as","which","who","whom",
        "how","what","when","where","why","we","they","he","she","i","you",
        "not","no","so","if","then","than","also","more","most","very"}

# ============================================================
# Vision backend (lazy singleton)
# ============================================================
_VISION_STATE = {
    "loaded": False,
    "backend": None,          # "clip" | "siglip" | None
    "model": None,
    "processor": None,
    "device": "cpu",
    "load_note": "",          
}
_VISION_LOCK = threading.Lock()


def _resolve_device() -> str:
    pref = os.environ.get("VISION_DEVICE", "auto").lower()
    if pref == "cpu":
        return "cpu"
    try:
        import torch
        if pref == "cuda":
            return "cuda" if torch.cuda.is_available() else "cpu"
        if pref == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"
    return "cpu"


def _try_load_clip(device: str):
    try:
        from transformers import CLIPModel, CLIPProcessor
        import torch
    except Exception as e:
        return None, f"transformers_or_torch_unavailable: {e}"
    model_name = os.environ.get("VISION_MODEL") or DEFAULT_CLIP_MODEL
    try:
        model = CLIPModel.from_pretrained(model_name).to(device).eval()
        processor = CLIPProcessor.from_pretrained(model_name)
        return (model, processor), f"clip_loaded:{model_name}"
    except Exception as e:
        return None, f"clip_load_failed: {e}"


def _try_load_siglip(device: str):
    try:
        from transformers import SiglipModel, SiglipProcessor
        import torch
    except Exception as e:
        return None, f"transformers_or_torch_unavailable: {e}"
    model_name = os.environ.get("VISION_MODEL") or DEFAULT_SIGLIP_MODEL
    try:
        model = SiglipModel.from_pretrained(model_name).to(device).eval()
        processor = SiglipProcessor.from_pretrained(model_name)
        return (model, processor), f"siglip_loaded:{model_name}"
    except Exception as e:
        return None, f"siglip_load_failed: {e}"


def load_vision_backend() -> Optional[str]:
    with _VISION_LOCK:
        if _VISION_STATE["loaded"]:
            return _VISION_STATE["backend"]
        _VISION_STATE["loaded"] = True

        mode = os.environ.get("VISION_BACKEND", "auto").lower()
        if mode == "none":
            _VISION_STATE["load_note"] = "disabled_by_env"
            return None

        device = _resolve_device()
        order = []
        if mode == "clip":
            order = [("clip", _try_load_clip)]
        elif mode == "siglip":
            order = [("siglip", _try_load_siglip)]
        else:
            order = [("siglip", _try_load_siglip), ("clip", _try_load_clip)]

        notes = []
        for name, loader in order:
            result, note = loader(device)
            notes.append(note)
            if result:
                model, processor = result
                _VISION_STATE["backend"] = name
                _VISION_STATE["model"] = model
                _VISION_STATE["processor"] = processor
                _VISION_STATE["device"] = device
                _VISION_STATE["load_note"] = note
                return name
        _VISION_STATE["backend"] = None
        _VISION_STATE["load_note"] = "; ".join(notes) or "no_backend_tried"
        return None


def _reset_vision_state() -> None:
    with _VISION_LOCK:
        _VISION_STATE.update({"loaded": False, "backend": None, "model": None,
                              "processor": None, "device": "cpu", "load_note": ""})


def vision_status() -> Dict:
    return {
        "loaded": _VISION_STATE["loaded"],
        "backend": _VISION_STATE["backend"],
        "device": _VISION_STATE["device"],
        "load_note": _VISION_STATE["load_note"],
    }


def score_frame_against_text(frame_path: str, visual_prompt: str) -> Optional[float]:
    backend = _VISION_STATE["backend"]
    model = _VISION_STATE["model"]
    processor = _VISION_STATE["processor"]
    if not backend or not model or not processor or not visual_prompt:
        return None
    if not frame_path or not Path(frame_path).exists():
        return None
    try:
        from PIL import Image
        import torch
        image = Image.open(frame_path).convert("RGB")
        inputs = processor(text=[visual_prompt], images=image,
                           return_tensors="pt", padding=True)
        device = _VISION_STATE["device"]
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model(**inputs)
        logits = outputs.logits_per_image.squeeze()
        if backend == "siglip":
            prob = torch.sigmoid(logits).item()
        else:
            scale = float(getattr(model, "logit_scale", None).exp().item()) \
                if getattr(model, "logit_scale", None) is not None else 100.0
            prob = torch.sigmoid(logits / scale).item()
        return max(0.0, min(1.0, prob))
    except Exception as e:
        print(f"VISION_SCORE_ERR: {e}")
        return None


# ============================================================
# FFmpeg helpers
# ============================================================
def _have_ffmpeg() -> bool:
    return bool(shutil.which("ffmpeg")) and bool(shutil.which("ffprobe"))


def _probe_duration(path: str) -> float:
    try:
        out = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", path
        ], timeout=20).decode().strip()
        return float(out)
    except Exception:
        return 0.0


def _extract_frames(video_path: str, tmp_dir: str,
                    interval: float = FRAME_SAMPLE_INTERVAL
                    ) -> List[Tuple[float, str]]:
    Path(tmp_dir).mkdir(parents=True, exist_ok=True)
    fps = 1.0 / max(interval, 0.1)
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"fps={fps:.3f}", "-q:v", "5",
            str(Path(tmp_dir) / "frame_%05d.jpg"),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
           timeout=180)
    except Exception:
        return []
    return [(i * interval, str(p))
            for i, p in enumerate(sorted(Path(tmp_dir).glob("frame_*.jpg")))]


def _brightness_std(path: str) -> Optional[Dict[str, float]]:
    try:
        from PIL import Image, ImageStat
    except Exception:
        return None
    try:
        stat = ImageStat.Stat(Image.open(path).convert("L"))
        return {"mean": stat.mean[0] / 255.0, "std": stat.stddev[0] / 255.0}
    except Exception:
        return None


def _frame_diff(a_path: str, b_path: str) -> Optional[float]:
    try:
        from PIL import Image, ImageChops, ImageStat
    except Exception:
        return None
    try:
        a = Image.open(a_path).convert("L").resize((160, 90))
        b = Image.open(b_path).convert("L").resize((160, 90))
        return ImageStat.Stat(ImageChops.difference(a, b)).mean[0] / 255.0
    except Exception:
        return None


def _tokens(text: str) -> set:
    if not text:
        return set()
    return {w for w in re.findall(r"[A-Za-z][A-Za-z\-]+", text.lower())
            if w not in STOP and len(w) > 2}


def _metadata_text(meta: Dict) -> str:
    return " ".join(meta.get(k, "") for k in ("tags", "title", "description", "filename")
                    if isinstance(meta.get(k), str))


def _windows(source_duration: float, target: float) -> List[Tuple[float, float]]:
    if source_duration <= 0 or target <= 0:
        return []
    if source_duration <= target:
        return [(0.0, source_duration)]
    out, start = [], 0.0
    while start + target <= source_duration + 1e-6:
        out.append((start, start + target))
        start += WINDOW_STEP_SECONDS
    if not out:
        out = [(0.0, min(target, source_duration))]
    return out


def _score_window(window, frames, scene_tokens, meta_tokens, metadata_present,
                  target_duration, frame_vision_scores, vision_backend) -> Dict:
    start, end = window
    dur = end - start

    if vision_backend and frame_vision_scores:
        win_frames = [(t, p) for t, p in frames if start <= t < end]
        vps = [frame_vision_scores[p] for _, p in win_frames if p in frame_vision_scores]
        if vps:
            semantic = sum(vps) / len(vps)
            semantic_source = vision_backend
        else:
            if scene_tokens and meta_tokens:
                semantic = len(scene_tokens & meta_tokens) / max(len(scene_tokens), 1)
            else:
                semantic = 0.30 if not metadata_present else 0.50
            semantic_source = "metadata_only"
    else:
        if scene_tokens and meta_tokens:
            semantic = len(scene_tokens & meta_tokens) / max(len(scene_tokens), 1)
        else:
            semantic = 0.30 if not metadata_present else 0.50
        semantic_source = "metadata_only"
    semantic = max(0.0, min(1.0, semantic))

    if scene_tokens and meta_tokens:
        entity = len(scene_tokens & meta_tokens) / max(len(scene_tokens), 1)
    else:
        entity = 0.30 if not metadata_present else 0.50
    entity = max(0.0, min(1.0, entity))

    win_frames = [(t, p) for t, p in frames if start <= t < end]
    qs = []
    for _, p in win_frames:
        s = _brightness_std(p)
        if not s:
            continue
        b = max(0.0, min(1.0, 1.0 - abs(s["mean"] - 0.5) * 2.0))
        st = min(1.0, s["std"] / 0.30)
        qs.append(0.6 * b + 0.4 * st)
    visual_quality = sum(qs) / len(qs) if qs else 0.50

    diffs = []
    for i in range(1, len(win_frames)):
        d = _frame_diff(win_frames[i - 1][1], win_frames[i][1])
        if d is not None:
            diffs.append(d)
    if diffs:
        m = sum(diffs) / len(diffs)
        if m < 0.02:
            stability = 0.40
        elif m > 0.25:
            stability = 0.30
        else:
            stability = max(0.30, min(1.0, 1.0 - abs(m - 0.08) * 4.0))
    else:
        stability = 0.50

    duration_fit = min(1.0, dur / target_duration) if target_duration > 0 else 0.0
    negative = 1.0

    if semantic_source in ("clip", "siglip"):
        w = {"semantic": 0.45, "entity": 0.10, "vq": 0.15, "st": 0.10, "dur": 0.10, "neg": 0.10}
    else:
        w = {"semantic": 0.25, "entity": 0.20, "vq": 0.15, "st": 0.15, "dur": 0.15, "neg": 0.10}
        
    final = (w["semantic"] * semantic + w["entity"] * entity +
             w["vq"] * visual_quality + w["st"] * stability +
             w["dur"] * duration_fit + w["neg"] * negative)

    if semantic_source == "metadata_only":
        final = min(final, 0.75)

    parts = []
    if semantic_source in ("clip", "siglip"):
        parts.append(f"Frames in this window have the highest visual similarity ({semantic_source}, avg={semantic:.2f}) to the scene visual prompt.")
    else:
        parts.append("visual semantic matching unavailable (no CLIP/SigLIP)")
        if not metadata_present:
            parts.append("no Pixabay metadata -> semantic/entity lowered")
    
    return {
        "semantic_match": round(semantic, 3),
        "semantic_match_source": semantic_source,
        "entity_match": round(entity, 3),
        "visual_quality": round(visual_quality, 3),
        "shot_stability": round(stability, 3),
        "duration_fit": round(duration_fit, 3),
        "negative_content": round(negative, 3),
        "final_score": round(final, 3),
        "confidence_explanation": "; ".join(parts),
    }


def select_segment(video_path: str, scene_narration: str, visual_goal: str,
                   search_queries: List[str], scene_duration: float,
                   metadata: Optional[Dict] = None,
                   persist_frames_to: Optional[str] = None,
                   visual_prompt: Optional[str] = None) -> Dict:
    prompt = (visual_prompt or visual_goal or "").strip()

    out = {
        "ok": False, "source_duration_sec": 0.0, "selected_start_sec": 0.0,
        "selected_end_sec": 0.0, "selected_duration_sec": 0.0, "score": 0.0,
        "score_breakdown": {}, "confidence_explanation": "", "review_required": True,
        "vision_backend": None, "vision_status": vision_status(), "visual_prompt": prompt,
        "selected_frame_paths": [], "method": "metadata_frames_ranking+vision" if prompt else "metadata_frames_ranking",
        "warnings": [],
    }
    if not video_path or not Path(video_path).exists():
        out["warnings"].append("source_video_missing"); return out
    if not _have_ffmpeg():
        out["warnings"].append("ffmpeg_or_ffprobe_missing"); return out

    src = _probe_duration(video_path)
    out["source_duration_sec"] = round(src, 3)
    if src <= 0:
        out["warnings"].append("source_duration_unknown"); return out

    target = max(MIN_CLIP_DURATION, min(MAX_CLIP_DURATION, scene_duration or 5.0))

    with tempfile.TemporaryDirectory(prefix="ke_frames_") as tmp:
        frames = _extract_frames(video_path, tmp)
        backend = load_vision_backend()
        out["vision_backend"] = backend
        out["vision_status"] = vision_status()
        
        frame_vision_scores: Dict[str, float] = {}
        if backend and prompt and frames:
            for _, fp in frames:
                s = score_frame_against_text(fp, prompt)
                if s is not None:
                    frame_vision_scores[fp] = s
            if not frame_vision_scores:
                out["warnings"].append("vision_backend_loaded_but_no_frame_scores")
                backend = None
                out["vision_backend"] = None

        scene_tokens = _tokens(" ".join([scene_narration or "", visual_goal or ""] + list(search_queries or [])))
        meta_text = _metadata_text(metadata or {})
        meta_tokens = _tokens(meta_text)
        metadata_present = bool(meta_tokens)

        for nk in NEGATIVE_KEYWORDS:
            if nk in meta_text.lower():
                out["warnings"].append(f"negative_keyword_in_metadata:{nk}")

        wins = _windows(src, target)
        if not wins:
            out["warnings"].append("no_windows_generated"); return out

        scored = [{"window": w, "score": _score_window(
            w, frames, scene_tokens, meta_tokens, metadata_present, target,
            frame_vision_scores, backend)} for w in wins]
        scored.sort(key=lambda x: x["score"]["final_score"], reverse=True)
        best = scored[0]
        start, end = best["window"]

        persisted: List[str] = []
        if persist_frames_to:
            pdir = Path(persist_frames_to)
            pdir.mkdir(parents=True, exist_ok=True)
            matching = [(t, p) for t, p in frames if start <= t < end][:5]
            for i, (_, p) in enumerate(matching):
                dst = pdir / f"selected_frame_{i:02d}.jpg"
                try:
                    shutil.copy(p, dst)
                    persisted.append(str(dst))
                except Exception:
                    pass

    score_bd = best["score"]
    review_required = (score_bd["final_score"] < SCORE_THRESHOLD or (not metadata_present and backend is None))

    out.update({
        "ok": True,
        "selected_start_sec": round(start, 3),
        "selected_end_sec": round(end, 3),
        "selected_duration_sec": round(end - start, 3),
        "score": score_bd["final_score"],
        "score_breakdown": {k: v for k, v in score_bd.items() if k not in ("final_score", "confidence_explanation")},
        "confidence_explanation": score_bd["confidence_explanation"],
        "review_required": review_required,
        "selected_frame_paths": persisted,
    })
    return out


def trim_video_segment(source_path: str, output_path: str, start_sec: float,
                       duration_sec: float, target_duration_sec: float) -> bool:
    if not Path(source_path).exists():
        return False
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    start_sec = max(0.0, start_sec)
    duration_sec = max(0.5, duration_sec)

    if duration_sec >= target_duration_sec - 0.1:
        cmd = ["ffmpeg", "-y", "-ss", f"{start_sec:.3f}", "-i", source_path,
               "-t", f"{duration_sec:.3f}", "-an",
               "-c:v", "libx264", "-preset", "fast", "-crf", "20",
               "-pix_fmt", "yuv420p", output_path]
    else:
        cmd = ["ffmpeg", "-y", "-ss", f"{start_sec:.3f}",
               "-stream_loop", "-1", "-i", source_path,
               "-t", f"{target_duration_sec:.3f}", "-an",
               "-c:v", "libx264", "-preset", "fast", "-crf", "20",
               "-pix_fmt", "yuv420p", output_path]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=300)
        return Path(output_path).exists() and Path(output_path).stat().st_size > 1024
    except Exception as e:
        print(f"TRIM_ERR: {e}")
        return False