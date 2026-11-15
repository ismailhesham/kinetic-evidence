from pipeline.media.providers import ai_generated

def test_ai_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ALLOW_AI_IMAGES", raising=False)
    hits = ai_generated.generate("snow leopard", "/tmp/ke_test_ai")
    assert hits == []