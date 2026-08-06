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


def _candidate_line(hit: SearchHit) -> str:
    why = "; ".join(hit.why[:2])
    return f"- {hit.routine.id} ({hit.score:.2f}): {hit.routine.title}; {why}; load: {hit.routine.body_path}"


def build_candidate_context(hits: list[SearchHit], max_chars: int = 700) -> str:
    candidates = [h for h in hits if h.score >= CANDIDATE_THRESHOLD]
    if not candidates:
        return ""
    lines = [
        "[Pensieve routine candidates]",
        "User appears to be asking for recall; inspect before concluding no tool/routine exists.",
    ]
    lines.extend(_candidate_line(h) for h in candidates[:3])
    return "\n".join(lines)[:max_chars]


def should_inject(hit: SearchHit) -> bool:
    """Return whether a hit is strong enough for hook context injection."""
    return hit.score >= _effective_threshold(hit)


def hook_json(hits: list[SearchHit]) -> str:
    if not hits:
        return "{}"
    if not should_inject(hits[0]):
        context = build_candidate_context(hits)
        if not context:
            return "{}"
    else:
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

