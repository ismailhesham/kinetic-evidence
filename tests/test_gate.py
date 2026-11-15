from pipeline import director, gate

def test_gate_fails_on_empty_audio():
    sc = director.split_into_scenes("Hello.", use_llm=False)[0]
    g = gate.check_scene(sc, media_ok=True, audio_ok=False)
    assert g["status"] == "FAILED"