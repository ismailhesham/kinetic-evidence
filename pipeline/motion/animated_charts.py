"""Animated charts: bars grow / lines draw over time."""
from __future__ import annotations
import re
from pathlib import Path

NUM_RE = re.compile(r"(-?\d[\d,]*(?:\.\d+)?)")

def _numbers(text):
    out = []
    for m in NUM_RE.finditer(text):
        try:
            out.append(float(m.group(1).replace(",", "")))
        except ValueError:
            continue
    return out

def render_animated_bar_chart(narration: str, out_dir: str,
                              duration: float = 2.0, fps: int = 30,
                              w: int = 1280, h: int = 720) -> dict:
    vals = _numbers(narration)
    if len(vals) < 2:
        return {"ok": False, "reason": "insufficient_data"}

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return {"ok": False, "reason": "matplotlib_unavailable"}

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    n_frames = max(int(duration * fps), 8)
    labels = [f"#{i+1}" for i in range(len(vals))]

    for f in range(n_frames):
        progress = f / max(n_frames - 1, 1)
        heights = [v * progress for v in vals]
        fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=100)
        fig.patch.set_facecolor("#0f1216")
        ax.set_facecolor("#0f1216")
        ax.tick_params(colors="#cfd6df")
        for sp in ax.spines.values():
            sp.set_color("#2b333e")
        ax.bar(labels, heights, color="#4f9dff")
        ax.set_ylim(0, max(vals) * 1.1)
        fig.tight_layout()
        fig.savefig(Path(out_dir) / f"frame_{f:04d}.png", facecolor=fig.get_facecolor())
        plt.close(fig)
    return {"ok": True, "frames_dir": str(out_dir), "pattern": str(Path(out_dir) / "frame_%04d.png"), "fps": fps, "n_frames": n_frames}