"""Extract visual elements from script text for editing only (no fact-checking)."""
from __future__ import annotations
import re
from typing import Dict, List

NUMBER_RE = re.compile(r"\b\d[\d,]*(?:\.\d+)?\b")
YEAR_RE = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")
PERCENT_RE = re.compile(r"\b\d+(?:\.\d+)?\s?%")
ORG_SUFFIX = r"(?:Inc\.?|Corp\.?|Corporation|Company|Ltd\.?|LLC|GmbH|Foundation|University|Institute|Agency|Ministry|Organization|Group)"
ORG_RE = re.compile(rf"\b([A-Z][A-Za-z&.\-]+(?:\s+[A-Z][A-Za-z&.\-]+)*\s+{ORG_SUFFIX})")
QUESTION_RE = re.compile(r"[^.!?]*\?")
QUOTE_RE = re.compile(r'"[^"]{3,200}"|“[^”]{3,200}”')
CAPS_TOKEN = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")


def extract(script: str) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {
        "numbers": [], "percentages": [], "years": [],
        "organizations": [], "names": [], "places": [],
        "quotes": [], "questions": [], "comparisons": [],
        "important_phrases": [],
    }
    out["numbers"] = NUMBER_RE.findall(script)
    out["percentages"] = PERCENT_RE.findall(script)
    out["years"] = YEAR_RE.findall(script)
    out["organizations"] = [m.group(1) for m in ORG_RE.finditer(script)]
    
    # Proper-noun candidates: capitalized sequences not at sentence start
    names = []
    for m in CAPS_TOKEN.finditer(script):
        token = m.group(0)
        prev = script[max(0, m.start() - 1)]
        if prev.isalpha() and prev.islower():
            continue
        names.append(token)
    out["names"] = names
    out["quotes"] = [q.strip('"“”') for q in QUOTE_RE.findall(script)]
    out["questions"] = [q.strip() for q in QUESTION_RE.findall(script)]
    
    for cmp in ["vs.", "versus", "compared to", "more than", "less than", "higher than", "lower than"]:
        if cmp in script.lower():
            out["comparisons"].append(cmp)
            
    for phrase in re.findall(r"[A-Z][^.!?]{10,90}[.!?]", script)[:10]:
        out["important_phrases"].append(phrase.strip())
    return out