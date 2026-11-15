"""
Director: English script → Scene list.

Order:
  1. Try DeepSeek (if DEEPSEEK_API_KEY present).
  2. Validate every scene narration is a contiguous substring of the script
     AND concatenation reproduces the script.
  3. If validation fails (or no key / network error), use the local director.

In ALL paths:
    original_narration == tts_narration
    display_text is a literal substring of original_narration
"""
from __future__ import annotations
import re
import uuid
from typing import List, Tuple, Dict, Any, Optional

from .schema import (Scene, Narration, KineticBlock, Evidence, AudioSpec,
                     Timeline, Technical, VisualPlan)
from . import visual_elements
from .llm import deepseek_client

# (We will import visual_plan in Part 3, but for now we use a basic fallback)
try:
    from . import visual_plan as visual_planner
except ImportError:
    visual_planner = None

SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")
WS = re.compile(r"\s+")

BEAT_MAP = [
    ("QUESTION", ["?"]),
    ("QUOTE", ['"', "“"]),
    ("STATISTICAL_CLAIM", ["%", "percent", "million", "billion", "trillion", "thousand"]),
    ("TIMELINE", [" in 19", " in 20", "year", "decade", "century"]),
    ("CONTRAST", [" however", " but ", " yet ", " on the other hand", " whereas"]),
    ("CONFLICT", [" conflict", " war", " dispute", " fight", " clash"]),
    ("RESULT", [" result", " outcome", " led to", " consequently", " because"]),
    ("CONCLUSION", [" finally", " in the end", " ultimately", " to conclude"]),
    ("PERSON", [" he ", " she ", " dr.", " mr.", " mrs.", " prof."]),
    ("PLACE", [" in ", " at ", " located"]),
    ("INTRODUCTION", [" first", " this is", " imagine"]),
]


# ---------- LOCAL DIRECTOR ----------

def _split_sentences(text: str) -> List[str]:
    text = text.replace("\r", " ").strip()
    if not text:
        return []
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    out: List[str] = []
    for p in paras:
        for s in SENT_SPLIT.split(p):
            s = s.strip()
            if s:
                out.append(s)
    return out


def _beat_type(sent: str) -> str:
    low = " " + sent.lower() + " "
    for beat, keys in BEAT_MAP:
        if any(k in low for k in keys):
            return beat
    return "CONTEXT"


def _chapter_for(beat: str) -> str:
    if beat == "INTRODUCTION":
        return "OPENING"
    if beat in ("STATISTICAL_CLAIM", "TIMELINE"):
        return "DATA"
    if beat in ("PERSON", "PLACE"):
        return "PEOPLE_PLACES"
    if beat in ("CONFLICT", "CONTRAST"):
        return "CONFLICT"
    if beat == "CONCLUSION":
        return "CLOSING"
    return "CONTEXT"


def _visual_goal(beat: str) -> Tuple[str, str]:
    if beat == "STATISTICAL_CLAIM":
        return "CHART", "Show the numeric claim."
    if beat == "TIMELINE":
        return "TIMELINE_CHART", "Show the dated sequence."
    if beat == "PERSON":
        return "EVIDENCE_CARD", "Show name/role callout."
    if beat == "PLACE":
        return "MAP", "Show location on a map."
    if beat == "QUOTE":
        return "DOCUMENT", "Show the quoted line."
    if beat == "QUESTION":
        return "EVIDENCE_CARD", "Display the question."
    if beat in ("CONTRAST", "CONFLICT"):
        return "BROLL", "Show a contrasting visual."
    return "BROLL", "Contextual b-roll or evidence card."


def _punctuation_only(narration: str) -> str:
    tokens = narration.split(" ")
    if len(tokens) > 22:
        mid = len(tokens) // 2
        if tokens[mid - 1][-1] not in ",.;:!?":
            tokens[mid - 1] = tokens[mid - 1] + ","
    return " ".join(tokens)


def _local_split(script: str, job_id: str) -> List[Scene]:
    sentences = _split_sentences(script)
    if not sentences:
        return []

    groups: List[List[str]] = []
    cur: List[str] = []
    cur_beat: Optional[str] = None
    for sent in sentences:
        beat = _beat_type(sent)
        if cur and beat != cur_beat and len(cur) >= 1:
            groups.append(cur); cur = [sent]; cur_beat = beat
        else:
            cur.append(sent); cur_beat = cur_beat or beat
        if len(cur) >= 3:
            groups.append(cur); cur = []; cur_beat = None
    if cur:
        groups.append(cur)

    scenes: List[Scene] = []
    for i, group in enumerate(groups, start=1):
        narration = " ".join(group)
        beat = _beat_type(narration)
        ev_type, goal = _visual_goal(beat)
        
        sc = Scene(
            scene_id=i, job_id=job_id, language="en",
            chapter=_chapter_for(beat), beat_type=beat,
            narration=Narration(
                original_narration=narration,
                tts_narration=narration,
                tts_punctuation_only=_punctuation_only(narration),
                on_screen_text="",
            ),
            evidence=Evidence(
                evidence_type=ev_type, visual_goal=goal, visual_prompt=goal,
                fallback_strategy="EVIDENCE_CARD",
                search_queries=[goal.replace("Show ", "").replace(".", "")],
            ),
            audio=AudioSpec(ambience_context="NEUTRAL"),
            technical=Technical(), timeline=Timeline(),
        )
        
        # Plan (If visual_plan exists, use it. Otherwise basic)
        if visual_planner:
            sc.visual_plan = visual_planner.build_visual_plan(sc)
        else:
            sc.visual_plan = VisualPlan(primary_visual_type=ev_type, fallback_visual_type="CARD")
            
        scenes.append(sc)
    return scenes


# ---------- LLM DIRECTOR ----------

def _validate_llm_scenes(script: str, data: dict) -> Optional[List[dict]]:
    """
    Accept LLM scenes ONLY if:
      - Each `narration` is a contiguous substring of the script.
      - Concatenation (whitespace-normalized) equals the script.
    """
    if not isinstance(data, dict):
        return None
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return None

    for s in scenes:
        if not isinstance(s, dict):
            return None
        narr = s.get("narration", "")
        if not isinstance(narr, str) or not narr.strip():
            return None
        if narr not in script:
            return None

    joined = " ".join(s["narration"] for s in scenes)
    if WS.sub(" ", script).strip() != WS.sub(" ", joined).strip():
        return None
    return scenes


def _build_scenes_from_llm(script: str, data: dict, job_id: str) -> Optional[List[Scene]]:
    validated = _validate_llm_scenes(script, data)
    if validated is None:
        return None

    scenes: List[Scene] = []
    for i, s in enumerate(validated, start=1):
        narration_text = s["narration"]
        beat = str(s.get("beat_type", "CONTEXT")).upper()
        chapter = str(s.get("chapter", _chapter_for(beat))).upper()
        evidence = s.get("evidence", {}) if isinstance(s.get("evidence"), dict) else {}
        ev_type = str(evidence.get("evidence_type", "BROLL")).upper()
        visual_goal = str(evidence.get("visual_goal", "Contextual visual."))
        visual_prompt = str(evidence.get("visual_prompt", visual_goal))
        fallback = str(evidence.get("fallback_strategy", "EVIDENCE_CARD")).upper()

        queries = s.get("search_queries")
        if not isinstance(queries, list) or not queries:
            queries = [visual_goal.replace(".", "").strip() or "documentary context"]

        sc = Scene(
            scene_id=i, job_id=job_id, language="en",
            chapter=chapter, beat_type=beat,
            narration=Narration(
                original_narration=narration_text,
                tts_narration=narration_text,
                tts_punctuation_only=_punctuation_only(narration_text),
                on_screen_text="",
            ),
            evidence=Evidence(
                evidence_type=ev_type,
                visual_goal=visual_goal,
                visual_prompt=visual_prompt,
                fallback_strategy=fallback,
                search_queries=[str(q) for q in queries],
            ),
            audio=AudioSpec(ambience_context="NEUTRAL"),
            technical=Technical(), timeline=Timeline(),
        )
        
        if visual_planner:
            sc.visual_plan = visual_planner.build_visual_plan(sc)
        else:
            sc.visual_plan = VisualPlan(primary_visual_type=ev_type, fallback_visual_type=fallback)
            
        scenes.append(sc)
    return scenes


# ---------- PUBLIC ENTRY ----------

def split_into_scenes(script: str, job_id: Optional[str] = None,
                      use_llm: bool = True) -> List[Scene]:
    job_id = job_id or f"job_{uuid.uuid4().hex[:8]}"
    if use_llm and deepseek_client.is_available():
        data = deepseek_client.analyze_script(script)
        if data:
            scenes = _build_scenes_from_llm(script, data, job_id)
            if scenes:
                return scenes
    return _local_split(script, job_id)