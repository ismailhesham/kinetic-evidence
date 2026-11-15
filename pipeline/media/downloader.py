"""Safe parallel downloader with retries, timeouts, integrity check."""
from __future__ import annotations
import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

DEFAULT_TIMEOUT = 20
MAX_RETRIES = 3


def _download_one(url: str, out_path: str, referer: str | None = None) -> bool:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path + ".part"
    headers = {"User-Agent": "KineticEvidence/1.0 (offline documentary)"}
    if referer:
        headers["Referer"] = referer
        
    for attempt in range(MAX_RETRIES):
        try:
            with requests.get(url, headers=headers, stream=True, timeout=DEFAULT_TIMEOUT) as r:
                r.raise_for_status()
                total = 0
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            total += len(chunk)
            if total > 1024:  # file must be > 1KB to be valid
                os.replace(tmp, out_path)
                return True
        except Exception:
            if os.path.exists(tmp):
                try: os.remove(tmp)
                except OSError: pass
            time.sleep(min(2 ** attempt, 6))
    return False


def download_many(items, out_dir: str, workers: int = 4):
    """items: list of dicts with 'url' and 'out_path'."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {}
        for it in items:
            futs[ex.submit(_download_one, it["url"], it["out_path"], it.get("referer"))] = it
        for fut in as_completed(futs):
            it = futs[fut]
            try:
                ok = fut.result()
            except Exception:
                ok = False
            results.append({"item": it, "ok": ok})
    return results