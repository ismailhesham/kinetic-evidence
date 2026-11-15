"""Safe-margin layout for on-screen text."""
SAFE_MARGIN_X = 0.08   # 8% left/right
SAFE_MARGIN_Y = 0.10   # 10% top/bottom

def safe_box(width: int, height: int):
    return (int(width * SAFE_MARGIN_X),
            int(height * SAFE_MARGIN_Y),
            int(width * (1 - SAFE_MARGIN_X)),
            int(height * (1 - SAFE_MARGIN_Y)))