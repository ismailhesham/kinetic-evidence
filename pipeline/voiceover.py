"""
English TTS: Kokoro → Piper → espeak-ng fallback. Never modifies words.
"""
from __future__ import annotations
import os, shutil, subprocess, wave
from pathlib import Path


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _espeak(text: str, out_path: str, speed: float = 1.0) -> bool:
    if not _have("espeak-ng") and not _have("espeak"):
        return False
    exe = "espeak-ng" if _have("espeak-ng") else "espeak"
    wpm = int(160 * max(0.5, min(2.0, speed)))
    cmd = [exe, "-v", "en-us", "-s", str(wpm), "-w", out_path, text]
    try:
        subprocess.run(cmd, check=True, timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return os.path.exists(out_path) and os.path.getsize(out_path) > 1000
    except Exception:
        return False


def _kokoro(text: str, out_path: str, speed: float = 1.0) -> bool:
    try:
        from kokoro import KPipeline
        import soundfile as sf
    except Exception:
        return False
    try:
        pipe = KPipeline(lang_code="a")
        chunks = [c.audio for c in pipe(text, voice="af_heart", speed=speed)]
        if not chunks:
            return False
        import numpy as np
        audio = np.concatenate([c.detach().cpu().numpy() if hasattr(c, "detach") else c for c in chunks])
        sf.write(out_path, audio, 24000)
        return os.path.exists(out_path) and os.path.getsize(out_path) > 1000
    except Exception:
        return False


def _piper(text: str, out_path: str, speed: float = 1.0) -> bool:
    try:
        from piper.voice import PiperVoice
    except Exception:
        return False
    model = os.environ.get("PIPER_MODEL")
    if not model or not os.path.exists(model):
        return False
    try:
        voice = PiperVoice.load(model)
        with wave.open(out_path, "wb") as wf:
            voice.synthesize(text, wf, length_scale=1.0 / max(0.5, speed))
        return os.path.exists(out_path) and os.path.getsize(out_path) > 1000
    except Exception:
        return False


def _silence_wav(path: str, seconds: float, sr: int = 44100) -> None:
    n = int(seconds * sr)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(b"\x00\x00" * n)


def synth_scene(text: str, out_path: str, speed: float = 1.0) -> dict:
    """Try Kokoro → Piper → espeak-ng → silence (never fail hard)."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    for name, fn in (("kokoro", _kokoro), ("piper", _piper), ("espeak", _espeak)):
        if fn(text, out_path, speed):
            return {"provider": name, "duration": wav_duration(out_path)}
            
    # Last resort: short silence so render continues
    est = max(1.5, len(text.split()) / 2.6)
    _silence_wav(out_path, est)
    return {"provider": "silence_fallback", "duration": est}


def wav_duration(path: str) -> float:
    try:
        with wave.open(path, "rb") as wf:
            return wf.getnframes() / float(wf.getframerate())
    except Exception:
        return 0.0


def concat_wavs(paths, out_path, sr=44100):
    """Concatenate mono 16-bit WAVs into one file."""
    import wave
    frames = []
    for p in paths:
        with wave.open(p, "rb") as wf:
            frames.append(wf.readframes(wf.getnframes()))
    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        for f in frames:
            wf.writeframes(f)