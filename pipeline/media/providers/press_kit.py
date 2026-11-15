"""Car manufacturer press rooms — discovery provider."""
from __future__ import annotations
from urllib.parse import quote

PRESS_ROOMS = {
    "toyota": "https://pressroom.toyota.com/", "lexus": "https://pressroom.lexus.com/",
    "honda": "https://hondanews.com/", "acura": "https://acuranews.com/",
    "ford": "https://media.ford.com/", "lincoln": "https://media.lincoln.com/",
    "gm": "https://media.gm.com/", "chevrolet": "https://media.chevrolet.com/",
    "cadillac": "https://media.cadillac.com/", "bmw": "https://www.press.bmwgroup.com/global/",
    "mercedes": "https://group-media.mercedes-benz.com/", "audi": "https://www.audi-mediacenter.com/",
    "porsche": "https://newsroom.porsche.com/", "volkswagen": "https://www.volkswagen-newsroom.com/",
    "vw": "https://www.volkswagen-newsroom.com/", "hyundai": "https://www.hyundai.news/",
    "kia": "https://press.kia.com/", "nissan": "https://global.nissannews.com/",
    "mazda": "https://newsroom.mazda.com/", "subaru": "https://media.subaru.com/",
    "volvo": "https://www.media.volvocars.com/", "stellantis": "https://www.media.stellantis.com/",
    "tesla": "https://www.tesla.com/press", "rivian": "https://rivian.com/newsroom",
    "lucid": "https://lucidmotors.com/media-room",
}

CAR_HINTS = {"car", "vehicle", "auto", "automobile", "suv", "truck",
             "sedan", "coupe", "hatchback", "ev", "electric car",
             "sports car", "supercar", "pickup"}

def _is_car_query(q: str) -> bool:
    ql = q.lower()
    return any(h in ql for h in CAR_HINTS) or any(b in ql for b in PRESS_ROOMS)

def search(query: str, kind: str = "video", limit: int = 5):
    if kind not in ("video", "image", "discovery"):
        return []
    if not _is_car_query(query):
        return []

    hits = []
    ql = query.lower()

    for brand, base in PRESS_ROOMS.items():
        if brand in ql:
            hits.append({
                "provider": "press_kit",
                "url": f"{base}search?q={quote(query)}" if "?" not in base else f"{base}&q={quote(query)}",
                "metadata": {
                    "kind": "discovery", "brand": brand, "base_url": base,
                    "license_type": "editorial_use_authorized",
                    "attribution_required": True,
                    "note": "Press kit — download manually. Editorial use is authorized but verify current terms per brand.",
                },
            })

    if not hits:
        for brand in ("toyota", "ford", "honda", "bmw", "mercedes", "hyundai", "kia", "volkswagen"):
            hits.append({
                "provider": "press_kit", "url": PRESS_ROOMS[brand],
                "metadata": {
                    "kind": "discovery", "brand": brand,
                    "license_type": "editorial_use_authorized", "attribution_required": True,
                },
            })
    return hits[:limit]