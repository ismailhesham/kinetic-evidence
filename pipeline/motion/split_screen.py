"""Split-screen comparison (side-by-side)."""
from __future__ import annotations

def build_hstack_filter(left_input: int, right_input: int,
                         left_label: str = "", right_label: str = "",
                         w: int = 1280, h: int = 720) -> str:
    half_w = w // 2
    parts = [
        f"[{left_input}:v]scale={half_w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={half_w}:{h},setsar=1[l]",
        f"[{right_input}:v]scale={half_w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={half_w}:{h},setsar=1[r]",
        "[l][r]hstack=inputs=2[stacked]",
    ]
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if left_label:
        lab = (left_label.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'"))
        parts.append(
            f"[stacked]drawtext=text='{lab}':fontfile={font}:fontsize=28:"
            f"fontcolor=white:x=30:y=30:box=1:boxcolor=black@0.6:boxborderw=10[v1]"
        )
    else:
        parts.append("[stacked]copy[v1]")
    if right_label:
        lab = (right_label.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'"))
        parts.append(
            f"[v1]drawtext=text='{lab}':fontfile={font}:fontsize=28:"
            f"fontcolor=white:x=w/2+30:y=30:box=1:boxcolor=black@0.6:boxborderw=10[vout]"
        )
    else:
        parts.append("[v1]copy[vout]")
    return ";".join(parts)