"""Simple map without geopandas: solid panel + location pin."""
from __future__ import annotations
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

GEO_DIR = Path("assets/geo")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def _font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except Exception:
        return ImageFont.load_default()

def render_map(location_label: str, out_path: str, geojson_name: str = None, w=1280, h=720) -> dict:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (w, h), "#0d1620")
    d = ImageDraw.Draw(img)
    for x in range(0, w, 80): d.line([(x, 0), (x, h)], fill="#12202c")
    for y in range(0, h, 80): d.line([(0, y), (w, y)], fill="#12202c")
    
    drawn = False
    if geojson_name:
        p = GEO_DIR / geojson_name
        if p.exists():
            try:
                gj = json.loads(p.read_text())
                coords = _collect_coords(gj)
                if coords:
                    xs = [c[0] for c in coords]; ys = [c[1] for c in coords]
                    minx, maxx = min(xs), max(xs)
                    miny, maxy = min(ys), max(ys)
                    def proj(x, y):
                        px = 80 + (x - minx) / (maxx - minx + 1e-6) * (w - 160)
                        py = h - 80 - (y - miny) / (maxy - miny + 1e-6) * (h - 160)
                        return px, py
                    for feature in gj.get("features", []):
                        polys = _polygons(feature.get("geometry", {}))
                        for poly in polys:
                            pts = [proj(*c) for c in poly]
                            if len(pts) > 2:
                                d.polygon(pts, outline="#59a4ff", fill="#1f3d5a")
                                drawn = True
            except Exception:
                pass
                
    if not drawn:
        d.rectangle([w // 2 - 200, h // 2 - 130, w // 2 + 200, h // 2 + 130], outline="#59a4ff", width=2)
    d.ellipse([w // 2 - 8, h // 2 - 8, w // 2 + 8, h // 2 + 8], fill="#ff5555")
    d.text((80, 80), "LOCATION", font=_font(22), fill="#8fb3ff")
    d.text((80, 120), location_label or "Unknown", font=_font(48), fill="#f3f7fb")
    img.save(out_path, "PNG")
    return {"ok": True, "path": out_path}

def _collect_coords(gj):
    out = []
    for f in gj.get("features", []):
        for poly in _polygons(f.get("geometry", {})):
            out.extend(poly)
    return out

def _polygons(geom):
    if geom.get("type") == "Polygon": return geom.get("coordinates", [])
    if geom.get("type") == "MultiPolygon":
        out = []
        for p in geom.get("coordinates", []): out.extend(p)
        return out
    return []