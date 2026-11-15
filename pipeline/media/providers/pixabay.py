"""Optional Pixabay provider (needs PIXABAY_API_KEY). Absent key → []."""
from __future__ import annotations
import os
import time
import requests

def search(query: str, kind: str = "video", limit: int = 3):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return []
    try:
        endpoint = "https://pixabay.com/api/videos/" if kind == "video" else "https://pixabay.com/api/"
        # حماية من الحظر: انتظر 0.7 ثانية قبل كل طلب
        time.sleep(0.7)
        
        r = requests.get(endpoint, params={
            "key": key, "q": query, "per_page": limit, "safesearch": "true"
        }, timeout=15)
        data = r.json()
        out = []
        for hit in data.get("hits", []):
            if kind == "video":
                v = hit["videos"].get("medium") or hit["videos"].get("small")
                if v:
                    out.append({"provider": "pixabay", "url": v["url"],
                                "metadata": {"tags": hit.get("tags", ""), "kind": kind}})
            else:
                out.append({"provider": "pixabay", "url": hit["webformatURL"],
                            "metadata": {"tags": hit.get("tags", ""), "kind": kind}})
        return out
    except Exception:
        return []