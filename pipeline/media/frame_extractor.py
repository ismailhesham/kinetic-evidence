"""Extract a frame from a video (used for basic visual inspection)."""
from __future__ import annotations
import subprocess
import os

def extract_frame(video_path: str, out_png: str, at_sec: float = 1.0) -> bool:
    cmd = ["ffmpeg", "-y", "-ss", str(at_sec), "-i", video_path,
           "-frames:v", "1", out_png]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        return os.path.exists(out_png) and os.path.getsize(out_png) > 500
    except Exception:
        return False