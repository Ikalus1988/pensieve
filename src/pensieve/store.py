from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import sqlite3
from typing import Iterable

from .routine import Routine, iter_routine_files, load_routine

ACTIVE_STATUSES = {"active"}
CONFIDENCE_BOOST = {"verified": 0.12, "observed": 0.04, "draft": 0.0}
COMPLAINT_PATTERNS = [
    "之前", "上次", "以前", "你之前", "你以前", "会干", "标准化", "流程", "pipeline", "skill",
    "少了哪一步", "哪一步", "质量不行", "今天不行", "怎么现在", "不记得",
]


@dataclass
class SearchHit:
    routine: Routine
    score: float
    why: list[str]


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS routines (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            type TEXT NOT NULL,
            status TEXT NOT NULL,
            confidence TEXT NOT NULL,
            aliases TEXT NOT NULL,
            trigger_phrases TEXT NOT NULL,
            cwd_hints TEXT NOT NULL,
            checklist TEXT NOT NULL,
            deliverables TEXT NOT NULL,
            tags TEXT NOT NULL,
            source_sessions TEXT NOT NULL,
            body_path TEXT NOT NULL,
            body TEXT NOT NULL,
            use_count INTEGER NOT NULL DEFAULT 0,
            reject_count INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS routine_fts USING fts5(
            id UNINDEXED,
            title,
            aliases,
            trigger_phrases,
            checklist,
            body
        );
        """
    )
    conn.commit()


def _dump(value: list[str]) -> str:
    return json.dumps(value, ensure_ascii=False)


def _load_list(row: sqlite3.Row, key: str) -> list[str]:
    try:
        value = json.loads(row[key])
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


def upsert_routine(conn: sqlite3.Connection, routine: Routine) -> None:
    conn.execute(
        """
        INSERT INTO routines (
            id,title,type,status,confidence,aliases,trigger_phrases,cwd_hints,checklist,
            deliverables,tags,source_sessions,body_path,body,updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,
            type=excluded.type,
            status=excluded.status,
            confidence=excluded.confidence,
            aliases=excluded.aliases,
            trigger_phrases=excluded.trigger_phrases,
            cwd_hints=excluded.cwd_hints,
            checklist=excluded.checklist,
            deliverables=excluded.deliverables,
            tags=excluded.tags,
            source_sessions=excluded.source_sessions,
            body_path=excluded.body_path,
            body=excluded.body,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            routine.id,
            routine.title,
            routine.type,
            routine.status,
            routine.confidence,
            _dump(routine.aliases),
            _dump(routine.trigger_phrases),
            _dump(routine.cwd_hints),
            _dump(routine.checklist),
            _dump(routine.deliverables),
            _dump(routine.tags),
            _dump(routine.source_sessions),
            routine.body_path,
            routine.body,
        ),
    )
    conn.execute("DELETE FROM routine_fts WHERE id = ?", (routine.id,))
    conn.execute(
        "INSERT INTO routine_fts (id,title,aliases,trigger_phrases,checklist,body) VALUES (?,?,?,?,?,?)",
        (
            routine.id,
            routine.title,
            " ".join(routine.aliases),
            " ".join(routine.trigger_phrases),
            " ".join(routine.checklist),
            routine.body,
        ),
    )
    conn.commit()


def index_cards(conn: sqlite3.Connection, cards_dir: Path) -> int:
    init_db(conn)
    count = 0
    for path in iter_routine_files(cards_dir) or []:
        upsert_routine(conn, load_routine(path))
        count += 1
    return count


def row_to_routine(row: sqlite3.Row) -> Routine:
    return Routine(
        id=row["id"],
        title=row["title"],
        type=row["type"],
        status=row["status"],
        confidence=row["confidence"],
        aliases=_load_list(row, "aliases"),
        trigger_phrases=_load_list(row, "trigger_phrases"),
        cwd_hints=_load_list(row, "cwd_hints"),
        checklist=_load_list(row, "checklist"),
        deliverables=_load_list(row, "deliverables"),
        tags=_load_list(row, "tags"),
        source_sessions=_load_list(row, "source_sessions"),
        body=row["body"],
        body_path=row["body_path"],
    )


def get_routine(conn: sqlite3.Connection, routine_id: str) -> Routine | None:
    init_db(conn)
    row = conn.execute("SELECT * FROM routines WHERE id = ?", (routine_id,)).fetchone()
    return row_to_routine(row) if row else None


def _update_card_status(routine: Routine, status: str) -> None:
    """Rewrite `status:` line in a routine's Markdown frontmatter.

    Uses the same `_FRONTMATTER_RE` parser as `routine.load_routine` so that
    a `---` literal embedded inside a frontmatter value (rare but YAML-legal)
    cannot trick this writer into splitting the frontmatter at the wrong
    offset.

    Silently no-ops if the file is missing, not .md, or has no frontmatter.
    """
    from .routine import _FRONTMATTER_RE

    path = Path(routine.body_path)
    if not path.exists() or path.suffix.lower() != ".md":
        return
    text = path.read_text(encoding="utf-8").lstrip("\ufeff")
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return
    head, end = text[: match.start()], match.end()
    fm_block = match.group(1)
    lines = fm_block.splitlines()
    changed = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("status:") or stripped.startswith("status :"):
            lines[i] = f"status: {status}"
            changed = True
            break
    if not changed:
        lines.append(f"status: {status}")
    new_fm = "\n".join(lines)
    # Rebuild: head + "---\n" + new frontmatter + "\n---" + original tail
    # after the closing fence. Using match.end() (start of "\n---" or end of
    # document) keeps the rest of the file byte-identical to the original.
    new_text = head + "---\n" + new_fm + "\n---" + text[match.end():]
    path.write_text(new_text, encoding="utf-8")


def set_status(conn: sqlite3.Connection, routine_id: str, status: str, *, persist_card: bool = True) -> Routine | None:
    init_db(conn)
    routine = get_routine(conn, routine_id)
    if routine is None:
        return None
    conn.execute("UPDATE routines SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, routine_id))
    conn.commit()
    if persist_card:
        routine.status = status
        _update_card_status(routine, status)
    return get_routine(conn, routine_id)


def reject_routine(conn: sqlite3.Connection, routine_id: str, *, persist_card: bool = False) -> Routine | None:
    init_db(conn)
    routine = set_status(conn, routine_id, "rejected", persist_card=persist_card)
    if routine is None:
        return None
    conn.execute("UPDATE routines SET reject_count = reject_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (routine_id,))
    conn.commit()
    return get_routine(conn, routine_id)


def supersede_routine(conn: sqlite3.Connection, routine_id: str, *, persist_card: bool = False) -> Routine | None:
    return set_status(conn, routine_id, "superseded", persist_card=persist_card)


def mark_used(conn: sqlite3.Connection, routine_id: str) -> None:
    init_db(conn)
    conn.execute("UPDATE routines SET use_count = use_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (routine_id,))
    conn.commit()


def stats(conn: sqlite3.Connection, routine_id: str) -> dict[str, int] | None:
    init_db(conn)
    row = conn.execute("SELECT use_count, reject_count FROM routines WHERE id = ?", (routine_id,)).fetchone()
    if row is None:
        return None
    return {"use_count": int(row["use_count"]), "reject_count": int(row["reject_count"])}


def _contains_any(text: str, needles: Iterable[str]) -> list[str]:
    text_l = text.lower()
    return [n for n in needles if n and n.lower() in text_l]


def _fts_query(query: str) -> str:
    terms = [t.strip('"') for t in query.replace("'", " ").replace('"', " ").split() if t.strip()]
    return " OR ".join(f'"{t}"' for t in terms[:12]) or '""'


def search(conn: sqlite3.Connection, query: str, cwd: str = "", limit: int = 5) -> list[SearchHit]:
    init_db(conn)
    q = query.strip()
    if not q:
        return []
    fts = _fts_query(q)
    rows = conn.execute(
        """
        SELECT r.*, bm25(routine_fts) AS rank
        FROM routine_fts
        JOIN routines r ON r.id = routine_fts.id
        WHERE routine_fts MATCH ?
          AND r.status IN ('active')
        ORDER BY rank
        LIMIT ?
        """,
        (fts, max(limit * 4, 10)),
    ).fetchall()

    recall_intent = bool(_contains_any(q, COMPLAINT_PATTERNS))
    seen = {row["id"] for row in rows}
    if recall_intent or not rows:
        extra = conn.execute("SELECT *, 0.0 AS rank FROM routines WHERE status IN ('active')").fetchall()
        rows = list(rows) + [row for row in extra if row["id"] not in seen]

    hits: list[SearchHit] = []
    for row in rows:
        routine = row_to_routine(row)
        why: list[str] = []
        raw_rank = float(row["rank"] or 0.0)
        fts_score = min(0.50, max(0.0, abs(raw_rank) / 10.0))
        score = fts_score

        trigger_matches = _contains_any(q, routine.trigger_phrases + routine.aliases)
        if trigger_matches:
            score += 0.35
            why.append("trigger: " + ", ".join(trigger_matches[:3]))
        if recall_intent:
            score += 0.12
            why.append("recall intent")
        if cwd:
            cwd_l = cwd.lower()
            cwd_matches = [h for h in routine.cwd_hints if h and (h.lower() in cwd_l or cwd_l in h.lower())]
            if cwd_matches:
                score += 0.18
                why.append("cwd match")
        score += CONFIDENCE_BOOST.get(routine.confidence, 0.0)
        if routine.confidence in CONFIDENCE_BOOST:
            why.append(f"confidence: {routine.confidence}")
        if not why:
            why.append("text match")
        hits.append(SearchHit(routine=routine, score=min(score, 1.0), why=why))

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]

