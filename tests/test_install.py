import json
from pathlib import Path

from pensieve.cli import _install_user_prompt_hook


def test_install_user_prompt_hook_is_idempotent(tmp_path):
    settings = tmp_path / "hooks.json"
    settings.write_text(json.dumps({"hooks": {"UserPromptSubmit": []}}), encoding="utf-8")

    _install_user_prompt_hook(settings, "pensieve hook --stdin", dry_run=False, backup_suffix=".bak")
    _install_user_prompt_hook(settings, "pensieve hook --stdin", dry_run=False, backup_suffix=".bak")

    data = json.loads(settings.read_text(encoding="utf-8"))
    hooks = data["hooks"]["UserPromptSubmit"]
    assert len(hooks) == 1
    assert hooks[0]["hooks"][0]["command"] == "pensieve hook --stdin"
    assert settings.with_suffix(settings.suffix + ".bak").exists()


def test_install_user_prompt_hook_preserves_existing_codex_hooks(tmp_path):
    settings = tmp_path / "hooks.json"
    existing = {
        "hooks": {
            "UserPromptSubmit": [
                {"matcher": "", "hooks": [{"type": "command", "command": "node termcanvas-hook.mjs", "timeout": 5}]}
            ],
            "PreToolUse": [
                {"matcher": "", "hooks": [{"type": "command", "command": "node termcanvas-hook.mjs", "timeout": 5}]}
            ],
        }
    }
    settings.write_text(json.dumps(existing), encoding="utf-8")

    _install_user_prompt_hook(settings, "pensieve hook --stdin", dry_run=False, backup_suffix=".bak")

    data = json.loads(settings.read_text(encoding="utf-8"))
    user_hooks = data["hooks"]["UserPromptSubmit"]
    assert len(user_hooks) == 2
    assert data["hooks"]["PreToolUse"] == existing["hooks"]["PreToolUse"]
    assert any("pensieve hook --stdin" in json.dumps(item) for item in user_hooks)
