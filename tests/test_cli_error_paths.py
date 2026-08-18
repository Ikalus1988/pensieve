"""CLI error path coverage — close the 56% coverage gap.

Every `cmd_<name>_not_found_returns_error` test covers a stderr path
that previously had zero coverage. The two `_read_hook_input` tests
freeze the new stderr warning added in PR #8.

Also tests `cmd_install_hook` PermissionError path (added in PR #8).
"""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from pensieve import cli


def _run(argv: list[str], stdin: str | None = None) -> tuple[int, str, str]:
    """Run cli.main() with optional stdin, capture (rc, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    old_stdin = sys.stdin
    try:
        if stdin is not None:
            sys.stdin = io.StringIO(stdin)
        with redirect_stdout(out), redirect_stderr(err):
            rc = cli.main(argv)
    finally:
        sys.stdin = old_stdin
    return rc, out.getvalue(), err.getvalue()


# --- cmd_add: file not found ----------------------------------------------


def test_cmd_add_file_not_found_returns_2(tmp_path):
    rc, out, err = _run(["--db", str(tmp_path / "p.sqlite3"), "add", str(tmp_path / "missing.md")])
    assert rc == 2
    assert "not found" in err
    assert out == ""


# --- cmd_get: not found ---------------------------------------------------


def test_cmd_get_not_found_returns_1(tmp_path):
    rc, out, err = _run(["--db", str(tmp_path / "p.sqlite3"), "get", "no-such-routine"])
    assert rc == 1
    assert "not found" in err
    assert out == ""


# --- cmd_reject: not found ------------------------------------------------


def test_cmd_reject_not_found_returns_1(tmp_path):
    rc, out, err = _run(["--db", str(tmp_path / "p.sqlite3"), "reject", "no-such-routine"])
    assert rc == 1
    assert "not found" in err


def test_cmd_supersede_not_found_returns_1(tmp_path):
    rc, out, err = _run(["--db", str(tmp_path / "p.sqlite3"), "supersede", "no-such-routine"])
    assert rc == 1
    assert "not found" in err


def test_cmd_supersede_with_by_arg(tmp_path, monkeypatch):
    """--by is accepted but only echoed; doesn't error."""
    rc, out, err = _run([
        "--db", str(tmp_path / "p.sqlite3"),
        "supersede", "no-such-routine", "--by", "replacement",
    ])
    assert rc == 1
    assert "not found" in err


# --- cmd_stats: not found ------------------------------------------------


def test_cmd_stats_not_found_returns_1(tmp_path):
    rc, out, err = _run(["--db", str(tmp_path / "p.sqlite3"), "stats", "no-such-routine"])
    assert rc == 1
    assert "not found" in err


# --- _read_hook_input: invalid JSON warns to stderr -----------------------


def test_read_hook_input_invalid_json_warns_on_stderr(monkeypatch):
    """PR #8: invalid JSON on stdin must surface a warning, not silently fall back."""
    import argparse

    args = argparse.Namespace(stdin=True, prompt="", cwd="")
    monkeypatch.setattr(sys, "stdin", io.StringIO("this is not valid json {"))
    err = io.StringIO()
    with redirect_stderr(err):
        prompt, cwd = cli._read_hook_input(args)
    assert prompt  # fell back to raw text
    assert "invalid JSON" in err.getvalue()


def test_read_hook_input_invalid_json_with_monkeypatched_stdin():
    """Simpler variant using monkeypatch.setattr pattern."""
    import argparse

    args = argparse.Namespace(stdin=True, prompt="", cwd="")
    sys.stdin = io.StringIO("not json at all")
    try:
        err = io.StringIO()
        with redirect_stderr(err):
            prompt, cwd = cli._read_hook_input(args)
    finally:
        sys.stdin = sys.__stdin__
    assert prompt
    assert "invalid JSON" in err.getvalue()


def test_read_hook_input_empty_stdin_uses_argv_prompt(monkeypatch):
    import argparse

    args = argparse.Namespace(stdin=True, prompt="from argv", cwd="/tmp")
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    with redirect_stderr(io.StringIO()):
        prompt, cwd = cli._read_hook_input(args)
    assert prompt == "from argv"
    assert cwd == "/tmp"


def test_read_hook_input_no_stdin_uses_argv_prompt():
    import argparse

    args = argparse.Namespace(stdin=False, prompt="from argv", cwd="/tmp")
    prompt, cwd = cli._read_hook_input(args)
    assert prompt == "from argv"
    assert cwd == "/tmp"


def test_read_hook_input_valid_json_extracts_prompt_and_cwd():
    import argparse

    args = argparse.Namespace(
        stdin=True, prompt="", cwd="",
    )
    payload = json.dumps({"prompt": "test prompt", "cwd": "/test/cwd"})
    sys.stdin = io.StringIO(payload)
    try:
        prompt, cwd = cli._read_hook_input(args)
    finally:
        sys.stdin = sys.__stdin__
    assert prompt == "test prompt"
    assert cwd == "/test/cwd"


def test_read_hook_input_valid_json_uses_alternative_keys():
    """The 5-key fallback list (prompt/userPrompt/user_prompt/message/text) must all extract."""
    import argparse

    for key in ("userPrompt", "user_prompt", "message", "text"):
        args = argparse.Namespace(stdin=True, prompt="", cwd="")
        payload = json.dumps({key: f"via {key}", "workdir": f"cwd via {key}"})
        sys.stdin = io.StringIO(payload)
        try:
            prompt, cwd = cli._read_hook_input(args)
        finally:
            sys.stdin = sys.__stdin__
        assert prompt == f"via {key}"
        assert cwd == f"cwd via {key}"


# --- cmd_install_hook: PermissionError returns 3 -------------------------


def test_cmd_install_hook_permission_error_returns_3(tmp_path, monkeypatch):
    """When settings.parent is unwritable, return 3 (not crash)."""
    unwritable = tmp_path / "no_perm"
    settings = unwritable / "deep" / "settings.json"

    from pensieve import cli as cli_mod

    def fake_install(settings_path, command, *, dry_run, backup_suffix):
        raise PermissionError(13, "Permission denied", str(settings_path.parent))

    monkeypatch.setattr(cli_mod, "_install_user_prompt_hook", fake_install)

    rc, out, err = _run(["install-hook", "--settings", str(settings)])
    assert rc == 3
    assert "cannot write" in err


def test_cmd_install_codex_hook_permission_error_returns_3(tmp_path, monkeypatch):
    unwritable = tmp_path / "no_perm"
    settings = unwritable / "deep" / "hooks.json"

    from pensieve import cli as cli_mod

    def fake_install(settings_path, command, *, dry_run, backup_suffix):
        raise PermissionError(13, "Permission denied", str(settings_path.parent))

    monkeypatch.setattr(cli_mod, "_install_user_prompt_hook", fake_install)

    rc, out, err = _run(["install-codex-hook", "--settings", str(settings)])
    assert rc == 3
    assert "cannot write" in err


# --- cmd_init / cmd_index with --home / --cards-dir ------------------------


def test_cmd_init_uses_custom_home_and_cards_dir(tmp_path):
    home = tmp_path / "my_home"
    cards = tmp_path / "my_cards"
    rc, out, err = _run([
        "--home", str(home),
        "--cards-dir", str(cards),
        "--db", str(tmp_path / "p.sqlite3"),
        "init",
    ])
    assert rc == 0
    assert home.exists()
    assert cards.exists()
    assert "Pensieve home" in out
    assert "Routine cards" in out


def test_cmd_index_uses_custom_cards_dir(tmp_path):
    cards = tmp_path / "custom_cards"
    cards.mkdir()
    (cards / "stub.md").write_text(
        "---\nid: stub\ntitle: Stub\nstatus: active\nconfidence: observed\n"
        "trigger_phrases:\n  - stub-trigger\n---\n# stub body\n",
        encoding="utf-8",
    )
    rc, out, err = _run([
        "--cards-dir", str(cards),
        "--db", str(tmp_path / "p.sqlite3"),
        "index",
    ])
    assert rc == 0
    assert "indexed 1 routine" in out


# --- cmd_search: --json output ------------------------------------------


def test_cmd_search_with_json_flag_emits_valid_json(tmp_path):
    rc, out, err = _run([
        "--db", str(tmp_path / "p.sqlite3"),
        "--cards-dir", "examples",
        "index",
    ])
    assert rc == 0
    rc, out, err = _run([
        "--db", str(tmp_path / "p.sqlite3"),
        "search", "完全无关的 prompt xyz123", "--json",
    ])
    assert rc == 0
    data = json.loads(out)
    assert isinstance(data, list)


# --- cmd_get with --json output -----------------------------------------


def test_cmd_get_with_json_flag_emits_valid_json(tmp_path):
    rc, out, err = _run([
        "--db", str(tmp_path / "p.sqlite3"),
        "--cards-dir", "examples",
        "index",
    ])
    assert rc == 0
    rc, out, err = _run([
        "--db", str(tmp_path / "p.sqlite3"),
        "get", "fanuc-payload-pipeline", "--json",
    ])
    assert rc == 0
    data = json.loads(out)
    assert data["id"] == "fanuc-payload-pipeline"
    assert "trigger_phrases" in data


def test_cmd_get_text_output_prints_body(tmp_path):
    rc, out, err = _run([
        "--db", str(tmp_path / "p.sqlite3"),
        "--cards-dir", "examples",
        "index",
    ])
    assert rc == 0
    rc, out, err = _run([
        "--db", str(tmp_path / "p.sqlite3"),
        "get", "fanuc-payload-pipeline",
    ])
    assert rc == 0
    assert "FANUC payload" in out or "sysvars" in out


# --- stdout reconfiguration ---------------------------------------------


def test_main_reconfigures_stdout_to_utf8(monkeypatch):
    """If stdout.reconfigure is available, it must be called with utf-8."""
    import pensieve.cli as cli_mod

    called = {"yes": False, "encoding": None}

    class FakeStdout:
        def reconfigure(self, **kw):
            called["yes"] = True
            called["encoding"] = kw.get("encoding")

        # cli.main() calls print(...) which writes to stdout; provide no-op
        # write/flush so the subcommand can finish without raising.
        def write(self, _):
            return 0

        def flush(self):
            return None

    monkeypatch.setattr(cli_mod.sys, "stdout", FakeStdout())
    # Run a subcommand that completes normally (--help triggers SystemExit
    # before reaching reconfigure, so we use a real subcommand)
    cli_mod.main(["--home", "/tmp/pensieve-test-home", "--db", "/tmp/never-read.sqlite3", "init"])
    assert called["yes"]
    assert called["encoding"] == "utf-8"