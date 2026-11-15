"""xfade transitions between scene clips (re-encodes; CPU fallback)."""
from __future__ import annotations
import subprocess
from pathlib import Path
from typing import List

def _probe_duration(path: str) -> float:
    try:
        out = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", path
        ], timeout=15).decode().strip()
        return float(out)
    except Exception:
        return 0.0

def concat_with_xfade(clip_paths: List[str], audio_path: str, out_path: str,
                      transition: str = "fade", duration: float = 0.5,
                      use_gpu: bool = False) -> bool:
    if not clip_paths:
        return False
        
    # 🛡️ صمام الأمان: لو المشاهد أكتر من 20، بنستخدم القطع المباشر عشان ميكراشش
    if len(clip_paths) > 20:
        print(f"> {len(clip_paths)} scenes detected: falling back to HARD CUTS to avoid FFmpeg crash.")
        return _concat_hard(clip_paths, audio_path, out_path, use_gpu)
        
    if len(clip_paths) == 1:
        return _mux_single(clip_paths[0], audio_path, out_path, use_gpu)

    durs = [_probe_duration(p) for p in clip_paths]
    if any(d <= 0 for d in durs):
        return _concat_hard(clip_paths, audio_path, out_path, use_gpu)

    inputs = []
    for p in clip_paths:
        inputs.extend(["-i", p])
    inputs.extend(["-i", audio_path])
    audio_idx = len(clip_paths)

    filter_parts = []
    prev = "[0:v]"
    cumulative = durs[0]
    for i in range(1, len(clip_paths)):
        offset = cumulative - duration
        out_label = f"[vx{i}]"
        filter_parts.append(
            f"{prev}[{i}:v]xfade=transition={transition}:"
            f"duration={duration}:offset={offset:.3f}{out_label}"
        )
        prev = out_label
        cumulative = cumulative + durs[i] - duration

    filter_parts.append(f"[{audio_idx}:a]anull[aout]")
    filter_complex = ";".join(filter_parts)

    codec = "h264_nvenc" if use_gpu else "libx264"
    codec_args = (["-preset", "p4", "-b:v", "5M"] if use_gpu
                  else ["-preset", "fast", "-crf", "20"])
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", filter_complex,
           "-map", prev, "-map", "[aout]",
           "-c:v", codec, *codec_args,
           "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", out_path]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=1800)
        return Path(out_path).exists() and Path(out_path).stat().st_size > 1024
    except Exception as e:
        print(f"XFADE_ERR: {e}")
        return _concat_hard(clip_paths, audio_path, out_path, use_gpu)

def _concat_hard(clip_paths, audio_path, out_path, use_gpu):
    concat_file = Path(clip_paths[0]).parent / "concat_hard.txt"
    with open(concat_file, "w") as f:
        for p in clip_paths:
            f.write(f"file '{Path(p).resolve()}'\n")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
           "-i", str(concat_file), "-i", audio_path,
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           "-shortest", "-movflags", "+faststart", out_path]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=1800)
        return True
    except Exception:
        return False

def _mux_single(clip_path, audio_path, out_path, use_gpu):
    codec = "h264_nvenc" if use_gpu else "libx264"
    cmd = ["ffmpeg", "-y", "-i", clip_path, "-i", audio_path,
           "-c:v", codec, "-c:a", "aac", "-b:a", "192k",
           "-shortest", "-movflags", "+faststart", out_path]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=600)
        return True
    except Exception:
        return False