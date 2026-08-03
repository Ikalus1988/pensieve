# Claude Code hook setup

Install the `UserPromptSubmit` hook:

```powershell
pensieve install-hook --dry-run
pensieve install-hook
```

The default hook command is:

```powershell
pensieve hook --stdin
```

`install-hook` edits `~/.claude/settings.json`, creates the parent directory if needed, and writes a backup next to the settings file before modifying an existing file.

## Runtime behavior

- The hook reads Claude Code hook JSON from stdin.
- It searches active routine cards.
- If the top match is high-confidence, it prints `hookSpecificOutput.additionalContext` and increments that routine's `use_count`.
- Otherwise it prints `{}`.

Pensieve intentionally injects only a short pointer to the routine card. The agent should load the card only if needed.

## Manual command

```powershell
'{"prompt":"之前那个机器人备份提取payload流程","cwd":"C:\\Users\\hp"}' | pensieve hook --stdin
```
