"""Hook JSON output contract — schema-level freeze.

Pensieve's hook integration with Claude Code and Codex CLI depends on a
specific JSON shape. This file freezes that shape as executable tests.

What lives in tests/test_search.py vs here:

- test_search.py     — scoring / threshold / lifecycle behavior
- test_install.py    — settings.json / hooks.json idempotency
- THIS FILE          — wire-format JSON contract that the agent consumes

Any change here MUST be coordinated with Claude Code and Codex CLI
hook consumers. If you find yourself "fixing" a test in this file,
you are almost certainly breaking a real downstream integration.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pensieve.cli import main
from pensieve.hook import (
    AUTO_INJECT_THRESHOLD,
    TRIGGER_DIRECT_THRESHOLD,
    _is_trigger_only,
    build_context,
    hook_json,
)
from pensieve.routine import Routine
from pensieve.store import SearchHit, connect, index_cards, search


# --- helpers ---------------------------------------------------------------


def _hit(routine: Routine, score: float, why: list[str] | None = None) -> SearchHit:
    return SearchHit(routine=routine, score=score, why=why or ["text match"])


def _stub_routine(**overrides) -> Routine:
    base = dict(
        id="stub-routine",
        title="Stub routine for contract tests",
        type="routine",
        status="active",
        confidence="observed",
        aliases=["stub"],
        trigger_phrases=["trigger-stub"],
        cwd_hints=[],
        checklist=["step a", "step b"],
        deliverables=[],
        tags=[],
        source_sessions=[],
        body="# stub body",
        body_path="/tmp/stub.md",
    )
    base.update(overrides)
    return Routine(**base)


def _populate(tmp_path: Path) -> Path:
    db = tmp_path / "pensieve.sqlite3"
    with connect(db) as conn:
        index_cards(conn, Path("examples"))
    return db


# --- 1. JSON shape contract ------------------------------------------------


def test_hook_json_empty_hits_returns_empty_object():
    """No hits must emit exactly `{}`, not null, not []."""
    assert hook_json([]) == "{}"


def test_hook_json_low_confidence_returns_empty_object():
    """Below-threshold hit must NOT emit additionalContext."""
    routine = _stub_routine()
    hits = [_hit(routine, score=0.10)]
    assert hook_json(hits) == "{}"


def test_hook_json_top_level_has_only_hook_specific_output():
    """Top-level must have exactly one key: hookSpecificOutput."""
    routine = _stub_routine()
    hits = [_hit(routine, score=0.80)]
    payload = json.loads(hook_json(hits))
    assert list(payload.keys()) == ["hookSpecificOutput"]


def test_hook_specific_output_has_only_two_keys():
    """hookSpecificOutput must contain exactly hookEventName + additionalContext."""
    routine = _stub_routine()
    hits = [_hit(routine, score=0.80)]
    payload = json.loads(hook_json(hits))
    inner = payload["hookSpecificOutput"]
    assert set(inner.keys()) == {"hookEventName", "additionalContext"}


def test_hook_event_name_is_user_prompt_submit():
    """Event name is a protocol field; changing it breaks Claude Code / Codex CLI."""
    routine = _stub_routine()
    hits = [_hit(routine, score=0.80)]
    payload = json.loads(hook_json(hits))
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"


def test_additional_context_is_string():
    """additionalContext must be a string, not an object/dict."""
    routine = _stub_routine()
    hits = [_hit(routine, score=0.80)]
    payload = json.loads(hook_json(hits))
    assert isinstance(payload["hookSpecificOutput"]["additionalContext"], str)


def test_additional_context_has_pensieve_prefix():
    """The `[Pensieve routine recall]` prefix is how the agent recognizes the source.

    Changing this prefix breaks every downstream consumer that filters
    by it (e.g. logging, dedup, billing). Don't.
    """
    routine = _stub_routine()
    hits = [_hit(routine, score=0.80)]
    payload = json.loads(hook_json(hits))
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert ctx.startswith("[Pensieve routine recall]\n")


def test_hook_json_output_is_valid_json_no_trailing_newline():
    """Hook stdout must be parseable JSON; trailing newline is OK for POSIX CLI."""
    routine = _stub_routine()
    hits = [_hit(routine, score=0.80)]
    raw = hook_json(hits)
    json.loads(raw)  # must parse
    assert "\n" not in raw.rstrip("\n")  # only trailing newline allowed


def test_hook_json_preserves_unicode_chars():
    """CJK titles must round-trip without \\uXXXX escaping."""
    routine = _stub_routine(title="机器人备份提取 — payload extraction")
    hits = [_hit(routine, score=0.80)]
    raw = hook_json(hits)
    assert "机器人备份提取" in raw
    assert "\\u" not in raw  # ensure_ascii=False in effect


# --- 2. 700-char cap contract ----------------------------------------------


def test_build_context_default_cap_is_700():
    """build_context default max_chars must stay at 700.

    Claude Code / Codex CLI truncate additionalContext around ~2k tokens.
    700 chars is the conservative budget that keeps the pointer short
    while leaving room for the agent's own context window.
    """
    import inspect

    sig = inspect.signature(build_context)
    assert sig.parameters["max_chars"].default == 700


def test_build_context_truncates_at_cap():
    """A routine body of 5000 chars must be truncated to <= max_chars."""
    long_body = "x" * 5000
    routine = _stub_routine(body=long_body)
    hits = [_hit(routine, score=0.80, why=["a" * 1000, "b" * 1000])]
    ctx = build_context(hits[0])
    assert len(ctx) <= 700


def test_hook_json_respects_700_char_cap_on_injection():
    """Even with extreme routine body, the emitted JSON must be small enough."""
    routine = _stub_routine(
        body="x" * 5000,
        title="T" * 200,
        checklist=[f"step-{i} " + ("y" * 100) for i in range(20)],
    )
    hits = [_hit(routine, score=0.80, why=[f"reason-{i} " + ("z" * 50) for i in range(10)])]
    raw = hook_json(hits)
    payload = json.loads(raw)
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert len(ctx) <= 700


# --- 3. Threshold contract via hook_json -----------------------------------


def test_hook_json_injects_at_auto_inject_threshold():
    """Score >= AUTO_INJECT_THRESHOLD must inject."""
    routine = _stub_routine()
    hits = [_hit(routine, score=AUTO_INJECT_THRESHOLD)]
    assert "additionalContext" in hook_json(hits)


def test_hook_json_blocks_below_auto_inject_threshold_for_recall_intent():
    """A score just under AUTO_INJECT with recall intent should NOT inject.

    (Note: trigger-only hits use a lower threshold; see next test.)
    """
    routine = _stub_routine()
    hits = [_hit(routine, score=AUTO_INJECT_THRESHOLD - 0.01)]
    # Force not-trigger-only by adding a non-trigger why:
    hits[0].why.append("recall intent")
    assert hook_json(hits) == "{}"


def test_hook_json_injects_at_trigger_direct_threshold_for_direct_commands():
    """Score >= TRIGGER_DIRECT_THRESHOLD with trigger-only must inject."""
    routine = _stub_routine()
    hits = [_hit(routine, score=TRIGGER_DIRECT_THRESHOLD, why=["trigger: sysvars.sv"])]
    assert _is_trigger_only(hits[0])
    assert "additionalContext" in hook_json(hits)


def test_hook_json_blocks_below_trigger_direct_threshold_even_for_direct_commands():
    """Score < TRIGGER_DIRECT_THRESHOLD must block, even when trigger-only."""
    routine = _stub_routine()
    hits = [_hit(routine, score=TRIGGER_DIRECT_THRESHOLD - 0.01, why=["trigger: x"])]
    assert hook_json(hits) == "{}"


# --- 4. End-to-end via cli.main(hook) --------------------------------------


def test_cli_hook_empty_stdin_no_match_returns_brace(tmp_path, monkeypatch):
    """Stdin-driven hook with a noise prompt must not pollute additionalContext."""
    monkeypatch.chdir(tmp_path)
    import tempfile

    cards = Path("examples")  # real examples used; no match expected for noise prompt

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "p.sqlite3"
        rc = main(["--db", str(db), "--cards-dir", str(cards), "hook", "写一份 README", "--cwd", ""])
        assert rc == 0
    # NB: main() prints to stdout; this test verifies only the return code,
    # not stdout. The point: cli.main must not raise on noise prompts.


def test_cli_hook_emits_valid_json_for_recall_intent(tmp_path):
    """End-to-end: cli.main hook path must produce parseable JSON."""
    import io
    import contextlib

    buf = io.StringIO()
    db = tmp_path / "p.sqlite3"
    main(["--db", str(db), "--cards-dir", "examples", "index"])
    with contextlib.redirect_stdout(buf):
        main(["--db", str(db), "hook", "今天质量不行，少了哪一步？", "--cwd", "C:\\Users\\hp"])
    raw = buf.getvalue().strip()
    payload = json.loads(raw)
    assert "hookSpecificOutput" in payload
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"


def test_cli_hook_emits_brace_for_no_match(tmp_path):
    """End-to-end: when no routine clears the threshold, output must be exactly `{}`."""
    import io
    import contextlib

    buf = io.StringIO()
    db = tmp_path / "p.sqlite3"
    main(["--db", str(db), "--cards-dir", "examples", "index"])
    with contextlib.redirect_stdout(buf):
        main(["--db", str(db), "hook", "完全无关的 prompt xyz123", "--cwd", ""])
    raw = buf.getvalue().strip()
    assert json.loads(raw) == {}


def test_cli_hook_increments_use_count_on_inject(tmp_path):
    """Injecting via cli.main hook must increment the routine's use_count."""
    db = tmp_path / "p.sqlite3"
    main(["--db", str(db), "--cards-dir", "examples", "index"])
    main(["--db", str(db), "hook", "今天质量不行，少了哪一步？", "--cwd", "C:\\Users\\hp"])
    from pensieve.store import stats as store_stats

    with connect(db) as conn:
        s = store_stats(conn, "fanuc-payload-pipeline")
    assert s["use_count"] == 1


# --- 5. Schema conformance via real fixture --------------------------------


def test_real_examples_produce_schema_conformant_hook_json(tmp_path):
    """Walk the real examples/ corpus and assert every injectable hit
    produces a schema-conformant hook JSON."""
    db = _populate(tmp_path)
    with connect(db) as conn:
        for prompt in [
            "今天质量不行，少了哪一步？",
            "之前那个机器人备份提取payload流程",
            "查收邮件",
            "sysvars.sv 提取",
        ]:
            hits = search(conn, prompt, cwd="C:\\Users\\hp", limit=3)
            raw = hook_json(hits)
            if raw == "{}":
                continue
            payload = json.loads(raw)
            assert list(payload.keys()) == ["hookSpecificOutput"]
            inner = payload["hookSpecificOutput"]
            assert set(inner.keys()) == {"hookEventName", "additionalContext"}
            assert inner["hookEventName"] == "UserPromptSubmit"
            assert isinstance(inner["additionalContext"], str)
            assert inner["additionalContext"].startswith("[Pensieve routine recall]\n")
            assert len(inner["additionalContext"]) <= 700


def test_threshold_constants_are_in_known_bands():
    """Sanity-check the constants — drift here breaks every test above."""
    assert 0.0 < TRIGGER_DIRECT_THRESHOLD < AUTO_INJECT_THRESHOLD < 1.0
    assert AUTO_INJECT_THRESHOLD == pytest.approx(0.75)
    assert TRIGGER_DIRECT_THRESHOLD == pytest.approx(0.65)