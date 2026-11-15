from pipeline import director
from pipeline.typography import engine

def test_kinetic_substring():
    scenes = director.split_into_scenes("The population reached 3 million in 2020.", use_llm=False)
    for s in scenes:
        s.kinetic = engine.build_kinetic_block(s)
        for ev in s.kinetic.events:
            assert ev.display_text in s.narration.original_narration