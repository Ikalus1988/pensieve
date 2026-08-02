# Pensieve

Recall validated routines from past coding-agent sessions.

Pensieve is a tiny local routine registry for Claude Code-style workflows. It is not a general memory layer. It stores and retrieves **procedural memories**: pipelines, checklists, delivery standards, and reusable skills that were validated in previous sessions.

## MVP scope

- Local YAML/Markdown routine cards
- SQLite FTS5 index
- High-threshold recall for `UserPromptSubmit` hooks
- Short `additionalContext` injection (path + checklist anchor, not full body)
- No vector DB, no Mem0, no automatic transcript extraction yet

## Install for development

```powershell
cd C:\Users\hp\pensieve
python -m pip install -e .
```

## Quick start

Create a routine:

```powershell
pensieve init
pensieve add examples\fanuc-payload-pipeline.md
pensieve index
pensieve search "之前那个机器人备份提取流程"
```

Hook-style recall:

```powershell
pensieve hook "今天提取的数据质量不行，少了哪一步？" --cwd C:\Users\hp
```

If a high-confidence routine matches, `hook` prints Claude Code hook JSON containing `additionalContext`. If not, it prints `{}`.

## Routine card format

A routine card is Markdown with YAML frontmatter:

```markdown
---
id: fanuc-payload-pipeline
title: FANUC payload extraction pipeline
type: pipeline
status: active
confidence: verified
aliases:
  - 机器人备份提取
  - fanuc payload
trigger_phrases:
  - 之前那个流程
  - 少了哪一步
cwd_hints:
  - C:\Users\hp
checklist:
  - locate sysvars.sv
  - parse PLST_GRP1
  - convert units
---
# FANUC payload extraction pipeline
...
```

## Why not just memory?

Facts are not enough. Pensieve recalls the workflow contract: when to use a routine, what deliverables are expected, and which checklist anchors prevent quality regressions.
