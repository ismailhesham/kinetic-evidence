from pipeline import director

def test_scene_split():
    script = ("One sentence here. Another sentence follows. "
              "The question is whether this works? "
              "In 2019 the figure reached 40%.")
    scenes = director.split_into_scenes(script)
    assert len(scenes) >= 2
    for s in scenes:
        assert s.narration.original_narration == s.narration.tts_narration
        assert s.language == "en"

def test_no_word_change():
    original = "In 2019 the Amazon lost 906,000 hectares."
    scenes = director.split_into_scenes(original, use_llm=False)
    joined = " ".join(s.narration.tts_narration for s in scenes)
    assert "2019" in joined and "906,000" in joined