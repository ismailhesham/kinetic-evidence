"""Wikimedia Commons — best source for specific species/objects."""
from __future__ import annotations
import re
import requests

SEARCH_URL = "https://commons.wikimedia.org/w/api.php"

def search(query: str, kind: str = "video", limit: int = 3):
    try:
        r = requests.get(SEARCH_URL, params={
            "action": "query", "format": "json",
            "generator": "search",
            "gsrsearch": f"filetype:{(kind or 'video')} {query}",
            "gsrlimit": limit, "gsrnamespace": 6,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size",
        }, timeout=20, headers={"User-Agent": "KineticEvidence/1.0"})
        data = r.json()
    except Exception:
        return []

    out = []
    for page in data.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("url")
        if not url:
            continue
        ext = info.get("extmetadata", {})
        license_short = ext.get("LicenseShortName", {}).get("value", "")
        artist = ext.get("Artist", {}).get("value", "")
        artist = re.sub(r"<[^>]+>", "", artist or "").strip()

        license_url = ext.get("LicenseUrl", {}).get("value", "")
        license_type = "cc_attribution_required"
        if "cc0" in license_short.lower() or "public domain" in license_short.lower():
            license_type = "public_domain"
        elif "cc" in license_short.lower():
            license_type = "cc_attribution_required"

        out.append({
            "provider": "wikimedia_commons",
            "url": url,
            "metadata": {
                "kind": kind, "title": page.get("title", ""),
                "artist": artist, "license_short": license_short,
                "license_url": license_url, "license_type": license_type,
                "attribution_required": license_type == "cc_attribution_required",
            },
        })
    return out