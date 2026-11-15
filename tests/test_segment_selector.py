from pipeline.media import segment_selector

def test_windows_never_exceed_source():
    for s, e in segment_selector._windows(30.0, 5.0):
        assert 0.0 <= s < e <= 30.0 + 1e-6
        assert (e - s) <= 5.0 + 1e-6