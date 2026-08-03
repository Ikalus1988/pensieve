from __future__ import annotations

import json
from .store import SearchHit

AUTO_INJECT_THRESHOLD = 0.75
TRIGGER_DIRECT_THRESHOLD = 0.65
CANDIDATE_THRESHOLD = 0.55


def _is_trigger_only(hit: SearchHit) -> bool:
    """Check if the match came from trigger phrases without recall intent."""
    why_set = set(hit.why)
    has_trigger = any(w.startswith("trigger:") for w in hit.why)
    has_recall = "recall intent" in why_set
    return has_trigger and not has_recall


def _effective_threshold(hit: SearchHit) -> float:
    """Return the injection threshold for this hit.

    Direct commands (e.g. "查收邮件") match trigger phrases but lack
    recall-intent keywords.  A lower threshold lets them through while
    keeping the stricter bar for ambiguous queries.
    """
    if _is_trigger_only(hit):
        return TRIGGER_DIRECT_THRESHOLD
    return AUTO_INJECT_THRESHOLD


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
    if not hits:
        return "{}"
    threshold = _effective_threshold(hits[0])
    if hits[0].score < threshold:
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
