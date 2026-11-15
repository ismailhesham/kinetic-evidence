"""Official crash test / safety videos — public domain."""
from __future__ import annotations
import requests

EURO_NCAP_BASE = "https://www.euroncap.com/en/results/"

def search(query: str, kind: str = "video", limit: int = 3):
    if kind != "video":
        return []
    ql = query.lower()
    if not any(h in ql for h in ("crash", "safety", "ncap", "nhtsa", "test", "rating")):
        return []

    hits = []
    hits.append({
        "provider": "official_safety",
        "url": f"https://www.nhtsa.gov/search?search_api_fulltext={requests.utils.quote(query)}",
        "metadata": {
            "kind": "discovery", "source": "NHTSA (US government, public domain)",
            "license_type": "public_domain", "attribution_required": False,
        },
    })
    if any(h in ql for h in ("euro", "ncap", "european")):
        hits.append({
            "provider": "official_safety", "url": EURO_NCAP_BASE,
            "metadata": {
                "kind": "discovery", "source": "Euro NCAP",
                "license_type": "editorial_use_authorized", "attribution_required": True,
            },
        })
    return hits[:limit]