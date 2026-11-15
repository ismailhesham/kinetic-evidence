import os, shutil, pytest
from pipeline import demo as demo_mod

@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not available")
def test_demo_produces_mp4(tmp_path):
    out = tmp_path / "demo.mp4"
    import sys
    sys.argv = ["demo", "--output", str(out)]
    demo_mod.main()
    assert out.exists() and os.path.getsize(out) > 20000