"""Word timestamps: whisperx/whisper → heuristic (word-count proportional)."""
from __future__ import annotations
import re
from typing import List
from .schema import WordTs

WORD_RE = re.compile(r"\S+")


def _heuristic(text: str, duration: float) -> List[WordTs]:
    words = WORD_RE.findall(text)
    if not words or duration <= 0:
        return []
    # weight by length, longer words take longer
    weights = [max(1, len(w)) for w in words]
    total = sum(weights)
    out = []
    t = 0.0
    for w, wt in zip(words, weights):
        d = duration * (wt / total)
        out.append(WordTs(word=w, start=round(t, 3), end=round(t + d, 3)))
        t += d
    return out


def _try_whisperx(text: str, audio_path: str) -> List[WordTs]:
    try:
        import whisperx
    except Exception:
        return []
    try:
        model = whisperx.load_model("tiny.en", "cpu", compute_type="int8")
        result = model.transcribe(audio_path)
        align_model, meta = whisperx.load_align_model(language_code="en", device="cpu")
        aligned = whisperx.align(result["segments"], align_model, meta, audio_path, "cpu")
        words = []
        for seg in aligned.get("segments", []):
            for w in seg.get("words", []):
                words.append(WordTs(word=w["word"].strip(),
                                    start=float(w["start"]), end=float(w["end"])))
        return words
    except Exception:
        return []


def align(text: str, audio_path: str, duration: float) -> List[WordTs]:
    w = _try_whisperx(text, audio_path)
    if w:
        return w
    return _heuristic(text, duration)