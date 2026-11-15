"""GPU detection and encoder selection."""
from __future__ import annotations
import subprocess
import shutil

def detect_nvenc() -> bool:
    if not shutil.which("ffmpeg"):
        return False
    try:
        out = subprocess.check_output(["ffmpeg", "-hide_banner", "-encoders"],
                                      stderr=subprocess.STDOUT, timeout=10).decode()
        if "h264_nvenc" not in out:
            return False
        # Try a tiny test encode
        test = subprocess.run(
            ["ffmpeg", "-hide_banner", "-y", "-f", "lavfi", "-i",
             "color=black:s=64x64:d=0.1", "-c:v", "h264_nvenc", "-f", "null", "-"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        return test.returncode == 0
    except Exception:
        return False

def pick_encoder(prefer_gpu: bool = True) -> str:
    if prefer_gpu and detect_nvenc():
        return "h264_nvenc"
    return "libx264"