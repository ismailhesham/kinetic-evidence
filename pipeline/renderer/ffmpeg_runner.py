"""FFmpeg wrapper with error parsing and duration probing."""
from __future__ import annotations
import subprocess
import shutil

def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None

def ffprobe_duration(path: str) -> float:
    try:
        out = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", path
        ], timeout=20).decode().strip()
        return float(out)
    except Exception:
        return 0.0

def run_ffmpeg(args: list, timeout: int = 900) -> bool:
    try:
        subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=timeout)
        return True
    except subprocess.CalledProcessError as e:
        print("FFMPEG_ERR:", e.stderr.decode(errors="ignore")[-1500:])
        return False
    except Exception as e:
        print("FFMPEG_EXC:", e)
        return False