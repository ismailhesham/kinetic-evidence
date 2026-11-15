import os
from pipeline.audio import mixer

def test_procedural_audio(tmp_path):
    p1 = str(tmp_path / "m.wav")
    mixer.procedural_music(1.0, p1)
    assert os.path.getsize(p1) > 1000