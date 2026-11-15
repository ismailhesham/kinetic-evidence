"""
DeepSeek LLM Director client.

Role: EDITORIAL ONLY.
- Segments the English script into scenes.
- Suggests beat_type / chapter / evidence_type / visual_goal / search_queries.
- NEVER rewrites, corrects, translates, or fact-checks the script.
- NEVER invents numbers, names, sources, or URLs.

If DEEPSEEK_API_KEY is missing or the call fails, returns None so the
local director takes over. The pipeline NEVER hard-fails on LLM errors.
"""
from __future__ import annotations
import json
import os
import time
from typing import Optional, Dict, Any

import requests

DEFAULT_BASE = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
TIMEOUT = 60
MAX_RETRIES = 3

SYSTEM_PROMPT = """You are a documentary script DIRECTOR. You analyze English documentary scripts and return STRUCTURED JSON only.

HARD RULES — violating any of these is a critical failure:
1. NEVER change, rephrase, correct, translate, or fact-check the script.
2. NEVER invent facts, numbers, names, sources, URLs, or citations.
3. Each scene's `narration` MUST be an EXACT contiguous substring of the input script — same words, same numbers, same punctuation.
4. Concatenating all scene `narration` values in order (with single spaces) MUST reproduce the full script.
5. You may ONLY segment, classify, and suggest editorial metadata.

Return ONLY valid JSON matching this schema:
{
  "scenes": [
    {
      "scene_id": 1,
      "narration": "exact verbatim substring from the script",
      "chapter": "OPENING|CONTEXT|DATA|PEOPLE_PLACES|CONFLICT|CLOSING",
      "beat_type": "INTRODUCTION|CONTEXT|STATISTICAL_CLAIM|PERSON|PLACE|TIMELINE|CONFLICT|CONTRAST|QUESTION|QUOTE|RESULT|CONCLUSION",
      "kinetic": {
        "eligible": true,
        "eligibility_reason": "STATISTICAL_NUMBER|NAME|PLACE|DATE|QUOTE|QUESTION|RESULT|ORDINARY_NARRATIVE",
        "suggested_preset": "FADE_UP|WORD_POP|NUMBER_ROLL|TRACKING_REVEAL|QUOTE_BUILD|KINETIC_STATEMENT|DATA_CALLOUT|DOCUMENT_HIGHLIGHT|MAP_CALLOUT|PHRASE_SCALE|SPLIT_REVEAL|FADE_DOWN|MASK_WIPE|HIGHLIGHT_SWEEP"
      },
      "evidence": {
        "evidence_type": "BROLL|CHART|DOCUMENT|MAP|EVIDENCE_CARD|TIMELINE_CHART",
        "visual_goal": "short English description of the intended visual",
        "visual_prompt": "detailed English visual description for video search, e.g. 'aerial view of dense green amazon rainforest canopy at sunrise'",
        "fallback_strategy": "EVIDENCE_CARD|CHART|DOCUMENT|MAP"
      },
      "search_queries": ["english query 1", "english query 2"]
    }
  ]
}
"""


def is_available() -> bool:
    return bool(os.environ.get("DEEPSEEK_API_KEY"))


def _post(url: str, headers: dict, payload: dict) -> Optional[dict]:
    """POST with retry + exponential backoff. Returns parsed JSON or None."""
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt == MAX_RETRIES - 1:
                return None
            time.sleep(min(2 ** attempt, 6))
    return None


def analyze_script(script: str) -> Optional[Dict[str, Any]]:
    """
    Send the English script to DeepSeek. Return parsed JSON dict or None.
    On any failure or missing key, returns None → caller uses local director.
    """
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None

    base = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE).rstrip("/")
    model = os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL)
    url = f"{base}/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": script},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    raw = _post(url, headers, payload)
    if not raw:
        return None

    try:
        content = raw["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception:
        return None