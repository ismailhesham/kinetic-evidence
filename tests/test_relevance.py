from pipeline.media import evaluator

def test_relevance_components():
    rel = evaluator.evaluate("amazon rainforest", {"provider": "local",
                            "metadata": {"filename": "amazon_forest.mp4", "kind": "video"}})
    for k in ("entity_overlap", "composite_score", "confidence_explanation", "review_required"):
        assert k in rel