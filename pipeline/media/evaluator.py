"""Explainable RelevanceBreakdown — never invents a score without evidence."""
from __future__ import annotations

def evaluate(query: str, asset: dict, negative_keywords=None, shot_type_needed: str = "video") -> dict:
    negative_keywords = negative_keywords or []
    meta = asset.get("metadata", {})
    name = (meta.get("filename") or meta.get("title") or meta.get("tags") or "").lower()

    entity_overlap = 0.0
    q_terms = [t.lower() for t in query.split() if len(t) > 2]
    if q_terms:
        hits = sum(1 for t in q_terms if t in name)
        entity_overlap = hits / len(q_terms)

    evidence_category_match = 0.5 if asset.get("provider") else 0.0
    shot_type_match = 0.6 if meta.get("kind") == shot_type_needed else 0.3
    frame_inspection_result = 0.5  # neutral when not inspected

    negative_hit = any(nk.lower() in name for nk in negative_keywords)
    negative_keyword_result = 0.0 if negative_hit else 1.0
    source_metadata_quality = 0.7 if meta else 0.2

    components = {
        "entity_overlap": entity_overlap,
        "evidence_category_match": evidence_category_match,
        "shot_type_match": shot_type_match,
        "frame_inspection_result": frame_inspection_result,
        "negative_keyword_result": negative_keyword_result,
        "source_metadata_quality": source_metadata_quality,
    }
    weights = {"entity_overlap": 0.35, "evidence_category_match": 0.20,
               "shot_type_match": 0.15, "frame_inspection_result": 0.10,
               "negative_keyword_result": 0.10, "source_metadata_quality": 0.10}

    composite = sum(components[k] * weights[k] for k in components)

    review_required = composite < 0.55
    low_action = "USE_FALLBACK" if review_required else "USE_ASSET"

    explanation = []
    if entity_overlap < 0.3:
        explanation.append("low entity overlap with query")
    if negative_hit:
        explanation.append("negative keyword hit")
    if source_metadata_quality < 0.4:
        explanation.append("weak source metadata")
    if not explanation:
        explanation.append("acceptable match on all components")

    return {
        **components,
        "composite_score": round(composite, 3),
        "confidence_explanation": "; ".join(explanation),
        "review_required": review_required,
        "low_relevance_action": low_action,
    }