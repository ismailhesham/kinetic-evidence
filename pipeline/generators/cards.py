"""Evidence cards (numbers, names, quotes, questions)."""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

def _font(size):
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

def render_card(text: str, out_path: str, label: str = "EVIDENCE", w=1280, h=720) -> dict:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (w, h), "#0b1117")
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, w - 40, h - 40], outline="#384657", width=3)
    d.text((80, 80), label.upper(), font=_font(22), fill="#8fb3ff")
    
    font = _font(56)
    y = 220
    line = ""
    for word in text.split():
        cand = (line + " " + word).strip()
        if d.textlength(cand, font=font) > (w - 200):
            d.text((80, y), line, font=font, fill="#f3f7fb")
            y += 68
            line = word
            if y > h - 150:
                break
        else:
            line = cand
    if line:
        d.text((80, y), line, font=font, fill="#f3f7fb")
    img.save(out_path, "PNG")
    return {"ok": True, "path": out_path}