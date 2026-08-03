from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_LIST_KEYS = {"aliases", "trigger_phrases", "cwd_hints", "checklist", "deliverables", "tags", "source_sessions"}


@dataclass
class Routine:
    id: str
    title: str
    type: str = "routine"
    status: str = "active"
    confidence: str = "observed"
    aliases: list[str] = field(default_factory=list)
    trigger_phrases: list[str] = field(default_factory=list)
    cwd_hints: list[str] = field(default_factory=list)
    checklist: list[str] = field(default_factory=list)
    deliverables: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    source_sessions: list[str] = field(default_factory=list)
    body: str = ""
    body_path: str = ""

    @property
    def checklist_anchor(self) -> str:
        items = self.checklist[:5]
        if not items:
            return "see routine card"
        return " -> ".join(items)


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the tiny YAML subset used by routine cards.

    This intentionally avoids a PyYAML dependency for the MVP. Supported forms:
    key: scalar
    key:
      - item
      - item
    """
    data: dict[str, Any] = {}
    current_key: str | None = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith("  - ") and current_key:
            existing = data.get(current_key)
            if not isinstance(existing, list):
                data[current_key] = []
            data[current_key].append(_strip_quotes(raw[4:]))
            continue
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        key = key.strip()
        value = value.strip()
        current_key = key
        if value == "":
            data[key] = [] if key in _LIST_KEYS else ""
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            data[key] = [] if not inner else [_strip_quotes(part) for part in inner.split(",")]
        else:
            data[key] = _strip_quotes(value)
    return data


def load_routine(path: Path) -> Routine:
    text = path.read_text(encoding="utf-8").lstrip("\ufeff")
    match = _FRONTMATTER_RE.match(text)
    meta: dict[str, Any] = {}
    body = text
    if match:
        meta = parse_simple_yaml(match.group(1))
        body = text[match.end():]
    rid = str(meta.get("id") or path.stem)
    title = str(meta.get("title") or rid.replace("-", " ")).strip()

    def as_list(name: str) -> list[str]:
        value = meta.get(name, [])
        if isinstance(value, list):
            return [str(v) for v in value if str(v).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    return Routine(
        id=rid,
        title=title,
        type=str(meta.get("type") or "routine"),
        status=str(meta.get("status") or "active"),
        confidence=str(meta.get("confidence") or "observed"),
        aliases=as_list("aliases"),
        trigger_phrases=as_list("trigger_phrases"),
        cwd_hints=as_list("cwd_hints"),
        checklist=as_list("checklist"),
        deliverables=as_list("deliverables"),
        tags=as_list("tags"),
        source_sessions=as_list("source_sessions"),
        body=body.strip(),
        body_path=str(path),
    )


def iter_routine_files(cards_dir: Path):
    if not cards_dir.exists():
        return
    yield from sorted(cards_dir.glob("*.md"))
