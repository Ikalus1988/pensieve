from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .hook import AUTO_INJECT_THRESHOLD, hook_json
from .paths import default_cards_dir, default_db_path, default_home, ensure_dirs
from .routine import load_routine
from .store import (
    connect,
    get_routine,
    index_cards,
    init_db,
    mark_used,
    reject_routine,
    search,
    stats,
    supersede_routine,
    upsert_routine,
)


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


def _read_hook_input(args) -> tuple[str, str]:
    if not args.stdin:
        return args.prompt or "", args.cwd or ""
    raw = sys.stdin.read()
    if not raw.strip():
        return args.prompt or "", args.cwd or ""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return args.prompt or raw, args.cwd or ""
    prompt = payload.get("prompt") or payload.get("userPrompt") or payload.get("message") or args.prompt or ""
    cwd = payload.get("cwd") or payload.get("currentWorkingDirectory") or payload.get("current_working_directory") or args.cwd or ""
    return str(prompt), str(cwd)


def cmd_hook(args) -> int:
    prompt, cwd = _read_hook_input(args)
    with _conn(args) as conn:
        hits = search(conn, prompt, cwd=cwd, limit=3)
        if hits and hits[0].score >= AUTO_INJECT_THRESHOLD:
            mark_used(conn, hits[0].routine.id)
    print(hook_json(hits))
    return 0


def cmd_reject(args) -> int:
    with _conn(args) as conn:
        routine = reject_routine(conn, args.id, persist_card=True)
    if routine is None:
        print(f"not found: {args.id}", file=sys.stderr)
        return 1
    print(f"rejected: {args.id}")
    return 0


def cmd_supersede(args) -> int:
    with _conn(args) as conn:
        routine = supersede_routine(conn, args.id, persist_card=True)
    if routine is None:
        print(f"not found: {args.id}", file=sys.stderr)
        return 1
    suffix = f" -> {args.by}" if args.by else ""
    print(f"superseded: {args.id}{suffix}")
    return 0


def cmd_stats(args) -> int:
    with _conn(args) as conn:
        result = stats(conn, args.id)
    if result is None:
        print(f"not found: {args.id}", file=sys.stderr)
        return 1
    print(json.dumps({"id": args.id, **result}, ensure_ascii=False, indent=2))
    return 0


def cmd_install_hook(args) -> int:
    settings = Path(args.settings).expanduser() if args.settings else Path.home() / ".claude" / "settings.json"
    command = args.command or "pensieve hook --stdin"
    entry = {"matcher": "", "hooks": [{"type": "command", "command": command}]}
    data = {}
    if settings.exists():
        data = json.loads(settings.read_text(encoding="utf-8-sig", errors="replace") or "{}")
    hooks = data.setdefault("hooks", {})
    event_hooks = hooks.setdefault("UserPromptSubmit", [])
    existing = json.dumps(event_hooks, ensure_ascii=False)
    if command not in existing:
        event_hooks.append(entry)
    if args.dry_run:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    settings.parent.mkdir(parents=True, exist_ok=True)
    if settings.exists():
        backup = settings.with_suffix(settings.suffix + ".pensieve.bak")
        shutil.copyfile(settings, backup)
    settings.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"installed UserPromptSubmit hook in {settings}")
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
    p.add_argument("prompt", nargs="?")
    p.add_argument("--cwd", default="")
    p.add_argument("--stdin", action="store_true", help="Read Claude Code hook JSON from stdin")
    p.set_defaults(func=cmd_hook)

    p = sub.add_parser("reject", help="Mark a routine as rejected and exclude it from recall")
    p.add_argument("id")
    p.set_defaults(func=cmd_reject)

    p = sub.add_parser("supersede", help="Mark a routine as superseded and exclude it from recall")
    p.add_argument("id")
    p.add_argument("--by", help="Optional replacement routine id")
    p.set_defaults(func=cmd_supersede)

    p = sub.add_parser("stats", help="Show routine use/reject counters")
    p.add_argument("id")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("install-hook", help="Install a Claude Code UserPromptSubmit hook")
    p.add_argument("--settings", help="Claude Code settings.json path")
    p.add_argument("--command", help="Hook command to install (default: pensieve hook --stdin)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_install_hook)
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


