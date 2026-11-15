"""FFmpeg drawtext animations (fade, slide, pop)."""
from __future__ import annotations
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

def _esc(s: str) -> str:
    return (s.replace("\\", "\\\\").replace(":", "\\:")
             .replace("'", "\\'").replace("%", "\\%").replace("\n", " "))

def build_kinetic_text(text: str, preset: str, start_t: float, end_t: float) -> str:
    """Returns a complex FFmpeg drawtext filter with movement/fade."""
    safe_text = _esc(text)
    font = _find_font(bold=True)
    
    # Base properties
    props = {
        "text": f"'{safe_text}'",
        "fontfile": font,
        "fontsize": 64,
        "fontcolor": "white",
        "box": 1,
        "boxcolor": "black@0.55",
        "boxborderw": 22,
        "enable": f"'between(t,{start_t:.2f},{end_t:.2f})'"
    }
    
    anim_dur = 0.3  # seconds
    hold_end = end_t - anim_dur
    
    if preset == "FADE_UP":
        # Starts 20px lower and transparent, slides up and fades in
        props["y"] = f"if(lt(t,{start_t}), h, if(lt(t,{start_t + anim_dur}), (h-text_h)/2 + 20*(1-(t-{start_t})/{anim_dur}), (h-text_h)/2))"
        props["alpha"] = f"if(lt(t,{start_t}), 0, if(lt(t,{start_t + anim_dur}), (t-{start_t})/{anim_dur}, 1))"
        
    elif preset == "WORD_POP":
        # Scales up (simulated by fontsize isn't possible in drawtext, so we fade in fast)
        props["alpha"] = f"if(lt(t,{start_t}), 0, if(lt(t,{start_t + 0.15}), (t-{start_t})/0.15, 1))"
        props["y"] = "(h-text_h)/2"
        
    elif preset == "KINETIC_STATEMENT":
        # Slight shake: x shifts left/right 5px rapidly for 0.5s
        props["x"] = f"if(lt(t,{start_t}), w, if(lt(t,{start_t + 0.5}), (w-text_w)/2 + 5*sin((t-{start_t})*50), (w-text_w)/2))"
        props["y"] = "(h-text_h)/2"
        
    else:  # Default center
        props["x"] = "(w-text_w)/2"
        props["y"] = "(h-text_h)/2"
        
    # Combine into FFmpeg syntax
    parts = []
    for k, v in props.items():
        if k in ("text", "fontfile", "enable"):
            parts.append(f"{k}={v}")
        elif k in ("alpha", "x", "y"):
            parts.append(f"{k}='{v}'")
        else:
            parts.append(f"{k}={v}")
            
    return "drawtext=" + ":".join(parts)