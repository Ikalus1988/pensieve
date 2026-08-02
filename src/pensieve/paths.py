from __future__ import annotations

import os
from pathlib import Path

APP_DIR_NAME = "pensieve"


def default_home() -> Path:
    override = os.environ.get("PENSIEVE_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".claude" / APP_DIR_NAME


def default_cards_dir() -> Path:
    override = os.environ.get("PENSIEVE_CARDS_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".claude" / "routines"


def default_db_path() -> Path:
    return default_home() / "pensieve.sqlite3"


def ensure_dirs(home: Path | None = None, cards_dir: Path | None = None) -> None:
    (home or default_home()).mkdir(parents=True, exist_ok=True)
    (cards_dir or default_cards_dir()).mkdir(parents=True, exist_ok=True)
