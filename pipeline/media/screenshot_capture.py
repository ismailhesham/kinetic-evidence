"""
Screenshot capture for news headlines (Playwright-based).
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, Optional


def is_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright
        return True
    except ImportError:
        return False


def capture(url: str, out_path: str, selector: Optional[str] = None,
            viewport=(1440, 900), wait_ms: int = 3000,
            timeout_ms: int = 20000) -> Dict:
    if not is_available():
        return {"ok": False, "reason": "playwright_unavailable"}

    try:
        from playwright.sync_api import sync_playwright
        import datetime
    except ImportError:
        return {"ok": False, "reason": "playwright_unavailable"}

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(wait_ms)

            for sel in ("[aria-label='Accept']", "button:has-text('Accept')",
                        "button:has-text('Agree')", "#onetrust-accept-btn-handler"):
                try:
                    page.locator(sel).first.click(timeout=1500)
                    page.wait_for_timeout(500)
                    break
                except Exception:
                    continue

            if selector:
                loc = page.locator(selector).first
                loc.wait_for(state="visible", timeout=8000)
                loc.screenshot(path=out_path)
            else:
                page.screenshot(path=out_path, full_page=False)

            browser.close()
            ok = Path(out_path).exists() and Path(out_path).stat().st_size > 1024

            return {
                "ok": ok,
                "path": out_path if ok else None,
                "url": url,
                "selector": selector,
                "captured_at": datetime.datetime.utcnow().isoformat() + "Z",
                "fair_use_note": "Brief excerpt for commentary/analysis. Credit displayed on screen. Review before publishing.",
                "license_type": "fair_use_editorial",
                "attribution_required": True,
                "review_required": True,
            }
        except Exception as e:
            try:
                browser.close()
            except Exception:
                pass
            return {"ok": False, "reason": f"capture_failed: {e}"}


def domain_credit(url: str) -> str:
    from urllib.parse import urlparse
    try:
        host = urlparse(url).netloc
        return host.replace("www.", "")
    except Exception:
        return url[:40]