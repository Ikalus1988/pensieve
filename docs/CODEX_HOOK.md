# Codex CLI hook setup

Pensieve can also be installed into Codex CLI's local hook file.

## Current compatibility

Codex stores hooks in:

```text
~/.codex/hooks.json
```

A typical existing file may already contain TermCanvas or other hooks under `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `SessionStart`, and `Stop`. Pensieve appends one extra `UserPromptSubmit` command and preserves existing entries.

## Install

Preview first:

```powershell
pensieve install-codex-hook --dry-run
```

Install:

```powershell
pensieve install-codex-hook
```

Default command:

```powershell
pensieve hook --stdin
```

The installer:

- edits `~/.codex/hooks.json`;
- creates `~/.codex/hooks.json.pensieve.bak` before modifying an existing file;
- is idempotent by command string, so re-running it does not add duplicates;
- preserves existing Codex hooks.

## Manual validation

```powershell
pensieve index
pensieve hook "之前那个机器人备份提取payload流程" --cwd C:\Users\hp
```

If the top routine score is high enough, Pensieve prints hook JSON with `hookSpecificOutput.additionalContext` and increments `use_count`.
