"""Internet Archive — public-domain + CC archive."""
from __future__ import annotations
import requests

SEARCH_URL = "https://archive.org/advancedsearch.php"
META_URL = "https://archive.org/metadata/{id}"

def search(query: str, kind: str = "video", limit: int = 3):
    if kind != "video":
        return []
    try:
        r = requests.get(SEARCH_URL, params={
            "q": f'({query}) AND mediatype:movies',
            "fl[]": ["identifier", "title", "description", "licenseurl", "creator"],
            "rows": min(limit * 3, 15), "output": "json",
        }, timeout=20, headers={"User-Agent": "KineticEvidence/1.0"})
        docs = r.json().get("response", {}).get("docs", [])
    except Exception:
        return []

    out = []
    for d in docs:
        ident = d.get("identifier")
        if not ident:
            continue
        try:
            meta = requests.get(META_URL.format(id=ident), timeout=15,
                                headers={"User-Agent": "KineticEvidence/1.0"}).json()
        except Exception:
            continue

        files = meta.get("files", []) or []
        mp4s = [f for f in files if f.get("name", "").lower().endswith(".mp4") and f.get("size") and int(f["size"]) > 100_000]
        if not mp4s:
            continue
        mp4s.sort(key=lambda f: int(f.get("size", 0)))
        chosen = mp4s[0]
        url = f"https://archive.org/download/{ident}/{chosen['name']}"

        license_url = d.get("licenseurl", "") or ""
        if not license_url:
            license_type = "unknown"
        elif "publicdomain" in license_url.lower() or "cc0" in license_url.lower():
            license_type = "public_domain"
        elif "creativecommons" in license_url.lower():
            license_type = "cc_attribution_required"
        else:
            license_type = "other"

        out.append({
            "provider": "internet_archive",
            "url": url,
            "metadata": {
                "kind": "video", "title": d.get("title", ""),
                "description": (d.get("description") or "")[:300],
                "creator": d.get("creator", ""), "identifier": ident,
                "license_url": license_url, "license_type": license_type,
                "attribution_required": license_type == "cc_attribution_required",
            },
        })
        if len(out) >= limit:
            break
    return out