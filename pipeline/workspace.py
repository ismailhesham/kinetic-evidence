"""Workspace helpers to organize job outputs."""
from __future__ import annotations
import json
import uuid
from pathlib import Path

ROOT = Path("workspaces")


def new_workspace() -> Path:
    p = ROOT / f"job_{uuid.uuid4().hex[:10]}"
    p.mkdir(parents=True, exist_ok=True)
    (p / "audio").mkdir(exist_ok=True)
    (p / "media").mkdir(exist_ok=True)
    (p / "scenes").mkdir(exist_ok=True)
    return p


def dump_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))