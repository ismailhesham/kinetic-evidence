"""Local cache to prevent re-downloading."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path

CACHE_DIR = Path(os.environ.get("KE_CACHE_DIR", "workspaces/_cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def key_for(provider: str, query: str, kind: str = "video") -> str:
    h = hashlib.sha256(f"{provider}|{kind}|{query}".encode()).hexdigest()[:24]
    return f"{provider}_{kind}_{h}"


def lookup(provider: str, query: str, kind: str = "video"):
    idx = CACHE_DIR / "index.json"
    if not idx.exists():
        return None
    try:
        data = json.loads(idx.read_text())
        k = key_for(provider, query, kind)
        entry = data.get(k)
        if entry and os.path.exists(entry["path"]):
            return entry
    except Exception:
        pass
    return None


def register(provider: str, query: str, path: str, kind: str = "video", meta=None):
    idx = CACHE_DIR / "index.json"
    try:
        data = json.loads(idx.read_text()) if idx.exists() else {}
        k = key_for(provider, query, kind)
        data[k] = {"path": str(path), "meta": meta or {}}
        idx.write_text(json.dumps(data, indent=2))
    except Exception:
        pass