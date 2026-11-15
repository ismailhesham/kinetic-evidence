"""Audio mixer: procedural music + ambience + sfx + ducking.
   Voiceover WAV is preserved at 44.1kHz mono 16-bit."""
from __future__ import annotations
import math, os, random, struct, wave
from pathlib import Path

SR = 44100

def _write(path, samples, sr=SR):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        for s in samples:
            v = max(-32768, min(32767, int(s * 32767)))
            wf.writeframes(struct.pack("<h", v))

def _read_wav(path):
    with wave.open(path, "rb") as wf:
        n = wf.getnframes()
        sr = wf.getframerate()
        raw = wf.readframes(n)
    samples = list(struct.unpack("<" + "h" * (len(raw) // 2), raw))
    return [s / 32768.0 for s in samples], sr

def procedural_music(duration: float, out_path: str, sr=SR) -> str:
    """Generate low pad music."""
    n = int(duration * sr)
    samples = []
    for i in range(n):
        t = i / sr
        # two detuned saws
        s = (math.sin(2 * math.pi * 110 * t) * 0.15 +
             math.sin(2 * math.pi * 165 * t) * 0.10 +
             math.sin(2 * math.pi * 220 * t) * 0.06)
        # gentle fade-in/out
        env = min(1.0, t / 1.2) * min(1.0, (duration - t) / 1.5)
        samples.append(s * env * 0.5)
    _write(out_path, samples, sr)
    return out_path

def procedural_ambience(duration: float, out_path: str, sr=SR, context="NEUTRAL") -> str:
    n = int(duration * sr)
    rng = random.Random(1234)
    samples = []
    for i in range(n):
        t = i / sr
        # filtered noise: low-pass by simple averaging
        noise = rng.uniform(-1, 1) * 0.02
        base = math.sin(2 * math.pi * (55 + context_param(context)) * t) * 0.02
        samples.append((noise + base) * min(1.0, t / 0.8) * min(1.0, (duration - t) / 0.8))
    _write(out_path, samples, sr)
    return out_path

def context_param(context):
    return {"URBAN": 8, "NATURE": 3, "TENSE": 15}.get(context, 5)

def mix_voice_with_bed(voice_path: str, music_path: str, ambience_path: str,
                       out_path: str, music_level=0.25, ambience_level=0.10,
                       ducking=True) -> str:
    """Read voice; overlay music+ambience, apply simple ducking during voice."""
    voice, sr = _read_wav(voice_path)
    music, _ = _read_wav(music_path) if os.path.exists(music_path) else ([], sr)
    amb, _ = _read_wav(ambience_path) if os.path.exists(ambience_path) else ([], sr)
    n = len(voice)
    out = [0.0] * n
    for i in range(n):
        v = voice[i]
        m = music[i] if i < len(music) else 0.0
        a = amb[i] if i < len(amb) else 0.0
        # Simple envelope: if voice present (>0.01) duck the bed by 6 dB
        duck = 0.5 if (ducking and abs(v) > 0.01) else 1.0
        out[i] = v * 0.95 + m * music_level * duck + a * ambience_level * duck
    _write(out_path, out, sr)
    return out_path