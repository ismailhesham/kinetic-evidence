from pipeline.motion import counters, lower_thirds

def test_counter_filter_extracts_number():
    assert counters.extract_number("400 HP") == 400.0

def test_lower_third_builds_filter():
    f = lower_thirds.build_lower_third("Source: Toyota")
    assert "drawtext" in f