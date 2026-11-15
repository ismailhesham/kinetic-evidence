"""NASA Image and Video Library — US government work, public domain."""
from __future__ import annotations
import requests

SEARCH_URL = "https://images-api.nasa.gov/search"
ASSET_URL = "https://images-api.nasa.gov/asset/{nasa_id}"

def search(query: str, kind: str = "video", limit: int = 3):
    if kind != "video":
        return []
    try:
        r = requests.get(SEARCH_URL, params={"q": query, "media_type": "video"},
                         timeout=20, headers={"User-Agent": "KineticEvidence/1.0"})
        items = r.json().get("collection", {}).get("items", [])
    except Exception:
        return []

    out = []
    for item in items[: limit * 2]:
        d = item.get("data", [{}])[0]
        nasa_id = d.get("nasa_id")
        if not nasa_id:
            continue
        try:
            asset = requests.get(ASSET_URL.format(nasa_id=nasa_id), timeout=15,
                                 headers={"User-Agent": "KineticEvidence/1.0"}).json()
        except Exception:
            continue
        mp4s = [h["href"] for h in asset.get("collection", {}).get("items", [])
                if h.get("href", "").lower().endswith(".mp4")]
        if not mp4s:
            continue
        mp4s.sort()
        out.append({
            "provider": "nasa", "url": mp4s[0],
            "metadata": {
                "kind": "video", "title": d.get("title", ""),
                "description": (d.get("description") or "")[:300],
                "nasa_id": nasa_id, "license_type": "public_domain",
                "attribution_required": False,
            },
        })
        if len(out) >= limit:
            break
    return out