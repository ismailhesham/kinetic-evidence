"""Local media provider: scans assets/media directory for usable files."""
from __future__ import annotations
import os
from pathlib import Path

MEDIA_DIR = Path(os.environ.get("KE_LOCAL_MEDIA", "assets/media"))

def search(query: str, kind: str = "video", limit: int = 3):
    results = []
    if not MEDIA_DIR.exists():
        return results
    q_terms = [t.lower() for t in query.split() if len(t) > 2]
    for f in MEDIA_DIR.rglob("*"):
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if kind == "video" and ext not in (".mp4", ".mov", ".mkv", ".webm"):
            continue
        if kind == "image" and ext not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        
        path_parts = [p.lower() for p in f.parts]
        haystack = " ".join(path_parts)
        
        score = sum(1 for t in q_terms if t in haystack)
        if any(t.replace(" ", "_") in path_parts for t in q_terms):
            score += 3
            
        if score > 0 or not q_terms:
            results.append({
                "provider": "local",
                "path": str(f),
                "score_hint": score,
                "metadata": {"filename": f.name, "kind": kind, "folders": path_parts},
            })
    results.sort(key=lambda r: r["score_hint"], reverse=True)
    return results[:limit]