"""Lower thirds: sliding name/source bar at bottom-left."""
from __future__ import annotations
from pathlib import Path

def _find_font(bold=False):
    for c in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        if Path(c).exists():
            return c
    return "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def build_lower_third(text: str, start_time: float = 0.5,
                       hold: float = 3.0, slide_ms: int = 300) -> str:
    if not text:
        return ""
    font = _find_font(bold=True)
    safe = (text.replace("\\", "\\\\").replace(":", "\\:")
                .replace("'", "\\'").replace("%", "\\%"))
    end = start_time + slide_ms / 1000.0
    hold_end = start_time + hold
    slide_s = slide_ms / 1000.0
    x_expr = (
        f"if(lt(t\\,{start_time:.3f})\\,-1000\\,"
        f"if(lt(t\\,{start_time + slide_s:.3f})\\,"
        f"-1000+(1060)*(t-{start_time:.3f})/{slide_s:.3f}\\,60))"
    )
    return (
        f"drawtext=text='{safe}':fontfile={font}:fontsize=32:"
        f"fontcolor=white:x='{x_expr}':y=h-140:"
        f"box=1:boxcolor=0x1a1a1a@0.85:boxborderw=18:"
        f"enable='between(t,{start_time:.2f},{hold_end:.2f})'"
    )