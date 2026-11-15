"""Animate a route being drawn on a map."""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw

def render_route_animation(base_map_path: str, out_dir: str, 
                           start_xy: tuple, end_xy: tuple, 
                           duration: float = 2.0, fps: int = 30) -> dict:
    if not Path(base_map_path).exists():
        return {"ok": False, "reason": "base_map_missing"}
        
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    base_img = Image.open(base_map_path).convert("RGBA")
    w, h = base_img.size
    
    # Scale coordinates to image size (assumes input is 0.0 to 1.0)
    x1, y1 = int(start_xy[0] * w), int(start_xy[1] * h)
    x2, y2 = int(end_xy[0] * w), int(end_xy[1] * h)
    
    n_frames = max(int(duration * fps), 8)
    
    for f in range(n_frames):
        progress = f / max(n_frames - 1, 1)
        frame = base_img.copy()
        draw = ImageDraw.Draw(frame)
        
        # Current position on the line
        cx = x1 + (x2 - x1) * progress
        cy = y1 + (y2 - y1) * progress
        
        # Draw route line
        draw.line([(x1, y1), (cx, cy)], fill=(255, 85, 85, 255), width=6)
        
        # Draw start dot
        draw.ellipse([x1 - 8, y1 - 8, x1 + 8, y1 + 8], fill=(79, 157, 255, 255))
        
        # Draw moving dot
        draw.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=(255, 255, 255, 255))
        
        frame.save(Path(out_dir) / f"frame_{f:04d}.png")

    return {
        "ok": True, 
        "frames_dir": str(out_dir), 
        "pattern": str(Path(out_dir) / "frame_%04d.png"),
        "fps": fps, 
        "n_frames": n_frames
    }