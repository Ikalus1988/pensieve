from __future__ import annotations

import json
from .store import SearchHit

AUTO_INJECT_THRESHOLD = 0.75
CANDIDATE_THRESHOLD = 0.55


def build_context(hit: SearchHit, max_chars: int = 700) -> str:
    routine = hit.routine
    why = "; ".join(hit.why[:3])
    text = (
        "[Pensieve routine recall]\n"
        f"Likely routine: {routine.id} — {routine.title}\n"
        f"Why matched: {why}.\n"
        f"Load if needed: {routine.body_path}\n"
        f"Checklist anchor: {routine.checklist_anchor}."
    )
    return text[:max_chars]


def hook_json(hits: list[SearchHit]) -> str:
    if not hits or hits[0].score < AUTO_INJECT_THRESHOLD:
        return "{}"
    context = build_context(hits[0])
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context,
            }
        },
        ensure_ascii=False,
    )
