"""Animate map pins dropping onto a static map image."""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw

def render_animated_pin(base_map_path: str, out_dir: str, duration: float = 1.5, fps: int = 30) -> dict:
    """
    Creates a sequence of frames where a red pin drops and bounces on the map.
    Returns dict with frames_dir and pattern.
    """
    if not Path(base_map_path).exists():
        return {"ok": False, "reason": "base_map_missing"}
        
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    base_img = Image.open(base_map_path).convert("RGBA")
    w, h = base_img.size
    
    # Pin target position (center)
    pin_x = w // 2
    pin_y = h // 2
    
    n_frames = max(int(duration * fps), 8)
    
    for f in range(n_frames):
        progress = f / max(n_frames - 1, 1)
        
        # Bounce effect math (starts high, drops, bounces slightly, rests)
        if progress < 0.6:
            # Falling
            offset_y = -300 * (1 - (progress / 0.6)**2) 
        elif progress < 0.8:
            # Bounce up
            offset_y = -30 * ((progress - 0.6) / 0.2) * (1 - (progress - 0.6) / 0.2)
        else:
            # Rest
            offset_y = 0
            
        current_y = int(pin_y + offset_y)
        
        # Copy base map and draw pin
        frame = base_img.copy()
        draw = ImageDraw.Draw(frame)
        
        # Draw pin (simple triangle + circle)
        pin_color = (255, 85, 85, 255)
        if current_y < h:
            # Pin shadow on ground
            if offset_y == 0:
                draw.ellipse([pin_x - 10, pin_y + 10, pin_x + 10, pin_y + 20], fill=(0, 0, 0, 100))
                
            # Pin shape
            draw.polygon([(pin_x, current_y), (pin_x - 15, current_y - 20), (pin_x + 15, current_y - 20)], fill=pin_color)
            draw.ellipse([pin_x - 12, current_y - 40, pin_x + 12, current_y - 16], fill=pin_color)
            draw.ellipse([pin_x - 5, current_y - 33, pin_x + 5, current_y - 23], fill=(255, 255, 255, 255))
            
        frame.save(Path(out_dir) / f"frame_{f:04d}.png")

    return {
        "ok": True, 
        "frames_dir": str(out_dir), 
        "pattern": str(Path(out_dir) / "frame_%04d.png"),
        "fps": fps, 
        "n_frames": n_frames
    }