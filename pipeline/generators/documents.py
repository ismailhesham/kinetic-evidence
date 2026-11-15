"""Paper-textured documents (Pillow)."""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
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

def render_document(narration: str, out_path: str, header: str = "EVIDENCE", w=1280, h=720) -> dict:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (w, h), "#f4ecd8")
    d = ImageDraw.Draw(img)
    for y in range(0, h, 6):
        d.line([(0, y), (w, y)], fill="#efe6d0")
    d.rectangle([60, 60, w - 60, h - 60], outline="#b8a888", width=2)
    d.text((80, 80), header, font=_font(28), fill="#3a2f1a")
    d.text((80, 130), "—", font=_font(20), fill="#3a2f1a")
    
    font = _font(30)
    y = 180
    line = ""
    for word in narration.split():
        cand = (line + " " + word).strip()
        if d.textlength(cand, font=font) > (w - 200):
            d.text((100, y), line, font=font, fill="#241a0e")
            y += 42
            line = word
            if y > h - 140:
                break
        else:
            line = cand
    if line and y < h - 140:
        d.text((100, y), line, font=font, fill="#241a0e")
    img.save(out_path, "PNG")
    return {"ok": True, "path": out_path}