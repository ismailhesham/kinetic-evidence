from pipeline.media import cache

def test_cache_roundtrip(tmp_path, monkeypatch):
    from pathlib import Path
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    f = tmp_path / "x.mp4"; f.write_bytes(b"0" * 2000)
    cache.register("local", "query", str(f))
    assert cache.lookup("local", "query") is not None