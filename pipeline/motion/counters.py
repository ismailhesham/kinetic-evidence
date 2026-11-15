"""Animated numeric counters via FFmpeg drawtext eif expressions."""
from __future__ import annotations
import re
from typing import Optional
from pathlib import Path

def _find_font(bold=True):
    for c in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]:
        if Path(c).exists():
            return c
    return "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def extract_number(text: str) -> Optional[float]:
    """Pull the first number from text (handles commas, percents)."""
    if not text:
        return None
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)", text)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None

def build_counter_filter(target_value: float, suffix: str = "",
                         start_time: float = 0.0, duration: float = 1.5,
                         fontsize: int = 120, color: str = "white") -> str:
    rate = (target_value / duration) if duration > 0 else target_value
    expr = f"trunc(min(t*{rate:.4f}\\,{target_value:g}))"
    text_body = f"%{{eif\\:{expr}\\:d}}"
    if suffix:
        full = f"{text_body} {suffix}"
    else:
        full = text_body
    font = _find_font(bold=True)
    enable = f"gte(t,{start_time:.2f})"
    return (
        f"drawtext=text='{full}':fontfile={font}:fontsize={fontsize}:"
        f"fontcolor={color}:x=(w-text_w)/2:y=(h-text_h)/2:"
        f"box=1:boxcolor=black@0.55:boxborderw=28:"
        f"enable='{enable}'"
    )

def build_counter_for_scene(scene, start_time: float = 0.3, duration: float = 1.5) -> Optional[str]:
    if not scene.kinetic or not scene.kinetic.events:
        return None
    ev = scene.kinetic.events[0]
    value = extract_number(ev.display_text) or extract_number(scene.narration.original_narration)
    if value is None or value <= 0:
        return None
    suffix = ""
    low = ev.display_text.lower()
    if "%" in ev.display_text: suffix = "%"
    elif "percent" in low: suffix = "%"
    elif "million" in low: suffix = "M"
    elif "billion" in low: suffix = "B"
    elif "hp" in low or "horsepower" in low: suffix = " HP"
    elif "km" in low: suffix = " km"
    elif "mph" in low: suffix = " mph"
    return build_counter_filter(value, suffix=suffix, start_time=start_time, duration=duration)