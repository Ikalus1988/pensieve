"""paths.py coverage — close the 68% gap.

Ambient env vars must be saved/restored so this file doesn't pollute
the developer's shell. The fixture below uses monkeypatch.setenv
which is auto-restored at test teardown.
"""

from __future__ import annotations

from pathlib import Path

from pensieve import paths


def test_default_home_uses_claude_dir_when_env_unset(monkeypatch):
    monkeypatch.delenv("PENSIEVE_HOME", raising=False)
    home = paths.default_home()
    assert home == Path.home() / ".claude" / "pensieve"


def test_default_home_uses_env_override(monkeypatch):
    monkeypatch.setenv("PENSIEVE_HOME", "/tmp/pensieve-override")
    assert paths.default_home() == Path("/tmp/pensieve-override")


def test_default_home_expandsuser(monkeypatch):
    monkeypatch.setenv("PENSIEVE_HOME", "~/my-pensieve")
    assert paths.default_home() == Path.home() / "my-pensieve"


def test_default_cards_dir_uses_claude_dir_when_env_unset(monkeypatch):
    monkeypatch.delenv("PENSIEVE_CARDS_DIR", raising=False)
    cards = paths.default_cards_dir()
    assert cards == Path.home() / ".claude" / "routines"


def test_default_cards_dir_uses_env_override(monkeypatch):
    monkeypatch.setenv("PENSIEVE_CARDS_DIR", "/tmp/my-cards")
    assert paths.default_cards_dir() == Path("/tmp/my-cards")


def test_default_db_path_is_under_default_home(monkeypatch):
    monkeypatch.delenv("PENSIEVE_HOME", raising=False)
    db = paths.default_db_path()
    assert db == paths.default_home() / "pensieve.sqlite3"


def test_default_db_path_picks_up_home_env_override(monkeypatch):
    monkeypatch.setenv("PENSIEVE_HOME", "/tmp/pensieve-override")
    db = paths.default_db_path()
    assert db == Path("/tmp/pensieve-override") / "pensieve.sqlite3"


def test_ensure_dirs_creates_both(monkeypatch, tmp_path):
    monkeypatch.setenv("PENSIEVE_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("PENSIEVE_CARDS_DIR", str(tmp_path / "cards"))
    paths.ensure_dirs()
    assert (tmp_path / "home").exists()
    assert (tmp_path / "cards").exists()


def test_ensure_dirs_accepts_explicit_args(tmp_path):
    home = tmp_path / "ehome"
    cards = tmp_path / "ecards"
    paths.ensure_dirs(home, cards)
    assert home.exists()
    assert cards.exists()


def test_ensure_dirs_idempotent(tmp_path):
    home = tmp_path / "home"
    cards = tmp_path / "cards"
    paths.ensure_dirs(home, cards)
    paths.ensure_dirs(home, cards)  # second call should not raise
    paths.ensure_dirs(home, cards)
    assert home.exists()
    assert cards.exists()