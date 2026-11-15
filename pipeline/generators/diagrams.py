"""Minimal Technical Diagram generator (Pillow only)."""
from __future__ import annotations
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

STOP = {"the","a","an","and","or","but","of","to","in","on","at","for",
        "with","by","from","that","this","these","those","is","are","was",
        "were","be","been","being","it","its","as","which","who","whom",
        "how","what","when","where","why","we","they","he","she","i","you",
        "not","no","so","if","then","than","also","more","most","very"}

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def _font(path, size):
    try: return ImageFont.truetype(path, size)
    except Exception: return ImageFont.load_default()

def _content_words(text: str, n: int = 3):
    words = re.findall(r"[A-Za-z][A-Za-z\-]+", text)
    kept = [w for w in words if w.lower() not in STOP and len(w) > 3]
    seen, out = set(), []
    for w in kept:
        if w.lower() in seen: continue
        seen.add(w.lower()); out.append(w)
        if len(out) >= n: break
    while len(out) < n: out.append(f"Step {len(out) + 1}")
    return out

def render_diagram(narration: str, out_path: str, w: int = 1280, h: int = 720) -> dict:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (w, h), "#0b1117")
    d = ImageDraw.Draw(img)

    labels = _content_words(narration, n=3)
    font_title = _font(FONT_BOLD, 28)
    font_node  = _font(FONT_BOLD, 22)

    d.text((60, 50), "PROCESS", font=font_title, fill="#8fb3ff")

    n = len(labels)
    box_w = int((w - 160) / n) - 40
    box_h = 160
    y = int(h / 2 - box_h / 2)
    boxes = []
    for i, label in enumerate(labels):
        x = 80 + i * (box_w + 40)
        boxes.append((x, y, x + box_w, y + box_h))
        d.rounded_rectangle(boxes[i], radius=16, outline="#4f9dff", fill="#132234", width=3)
        line = ""
        ty = y + 40
        for word in label.split():
            cand = (line + " " + word).strip()
            if d.textlength(cand, font=font_node) > box_w - 20:
                tw = d.textlength(line, font=font_node)
                d.text((x + (box_w - tw) / 2, ty), line, font=font_node, fill="#ffffff")
                ty += 30; line = word
            else: line = cand
        if line:
            tw = d.textlength(line, font=font_node)
            d.text((x + (box_w - tw) / 2, ty), line, font=font_node, fill="#ffffff")

    for i in range(len(boxes) - 1):
        x1 = boxes[i][2]
        x2 = boxes[i + 1][0]
        cy = (boxes[i][1] + boxes[i][3]) // 2
        d.line([(x1 + 6, cy), (x2 - 6, cy)], fill="#6fb3ff", width=4)
        d.polygon([(x2 - 6, cy), (x2 - 20, cy - 8), (x2 - 20, cy + 8)], fill="#6fb3ff")

    img.save(out_path, "PNG")
    return {"ok": True, "path": out_path, "labels": labels}