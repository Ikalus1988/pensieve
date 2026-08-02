from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .hook import hook_json
from .paths import default_cards_dir, default_db_path, default_home, ensure_dirs
from .routine import load_routine
from .store import connect, get_routine, index_cards, init_db, search, upsert_routine


def _conn(args):
    return connect(Path(args.db).expanduser() if args.db else default_db_path())


def cmd_init(args) -> int:
    ensure_dirs(Path(args.home).expanduser() if args.home else default_home(), Path(args.cards_dir).expanduser() if args.cards_dir else default_cards_dir())
    with _conn(args) as conn:
        init_db(conn)
    print(f"Pensieve home: {Path(args.home).expanduser() if args.home else default_home()}")
    print(f"Routine cards: {Path(args.cards_dir).expanduser() if args.cards_dir else default_cards_dir()}")
    print(f"Database: {Path(args.db).expanduser() if args.db else default_db_path()}")
    return 0


def cmd_add(args) -> int:
    ensure_dirs(cards_dir=Path(args.cards_dir).expanduser() if args.cards_dir else default_cards_dir())
    src = Path(args.file).expanduser()
    if not src.exists():
        print(f"not found: {src}", file=sys.stderr)
        return 2
    routine = load_routine(src)
    dst_dir = Path(args.cards_dir).expanduser() if args.cards_dir else default_cards_dir()
    dst = dst_dir / f"{routine.id}.md"
    if src.resolve() != dst.resolve():
        shutil.copyfile(src, dst)
    with _conn(args) as conn:
        init_db(conn)
        upsert_routine(conn, load_routine(dst))
    print(f"added: {routine.id} -> {dst}")
    return 0


def cmd_index(args) -> int:
    cards_dir = Path(args.cards_dir).expanduser() if args.cards_dir else default_cards_dir()
    ensure_dirs(cards_dir=cards_dir)
    with _conn(args) as conn:
        count = index_cards(conn, cards_dir)
    print(f"indexed {count} routine(s) from {cards_dir}")
    return 0


def cmd_search(args) -> int:
    with _conn(args) as conn:
        hits = search(conn, args.query, cwd=args.cwd or "", limit=args.limit)
    if args.json:
        print(json.dumps([
            {
                "id": h.routine.id,
                "title": h.routine.title,
                "score": round(h.score, 4),
                "why": h.why,
                "body_path": h.routine.body_path,
                "checklist_anchor": h.routine.checklist_anchor,
            }
            for h in hits
        ], ensure_ascii=False, indent=2))
        return 0
    for h in hits:
        print(f"{h.score:.3f}\t{h.routine.id}\t{h.routine.title}")
        print(f"     why: {'; '.join(h.why)}")
        print(f"     path: {h.routine.body_path}")
        print(f"     checklist: {h.routine.checklist_anchor}")
    return 0


def cmd_get(args) -> int:
    with _conn(args) as conn:
        routine = get_routine(conn, args.id)
    if routine is None:
        print(f"not found: {args.id}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(routine.__dict__, ensure_ascii=False, indent=2))
    else:
        print(routine.body)
    return 0


def cmd_hook(args) -> int:
    with _conn(args) as conn:
        hits = search(conn, args.prompt, cwd=args.cwd or "", limit=3)
    print(hook_json(hits))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pensieve", description="Recall validated routines from past coding-agent sessions.")
    parser.add_argument("--db", help="SQLite database path (default: ~/.claude/pensieve/pensieve.sqlite3)")
    parser.add_argument("--cards-dir", help="Routine cards directory (default: ~/.claude/routines)")
    parser.add_argument("--home", help="Pensieve home directory")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="Create local directories and database")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("add", help="Copy a routine card into the cards directory and index it")
    p.add_argument("file")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("index", help="Rebuild/update index from routine cards")
    p.set_defaults(func=cmd_index)

    p = sub.add_parser("search", help="Search routines")
    p.add_argument("query")
    p.add_argument("--cwd", default="")
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("get", help="Print routine body")
    p.add_argument("id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("hook", help="Emit Claude Code UserPromptSubmit hook JSON for a prompt")
    p.add_argument("prompt")
    p.add_argument("--cwd", default="")
    p.set_defaults(func=cmd_hook)
    return parser


def main(argv: list[str] | None = None) -> int:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
