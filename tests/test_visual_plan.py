from pipeline import director, visual_plan

def test_place_scene_has_map_pin():
    sc = director.split_into_scenes("The city of Kyoto is located in Japan.", use_llm=False)[0]
    p = visual_plan.build_visual_plan(sc)
    assert p.primary_visual_type == "BROLL"
    assert "MAP_PIN" in p.secondary_layers
    assert p.fallback_visual_type == "MAP"