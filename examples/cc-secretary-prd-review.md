---
id: cc-secretary-prd-review
title: Claude Code secretary PRD review routine
type: checklist
status: active
confidence: verified
aliases:
  - cc-secretary PRD
  - pensieve PRD review
  - routine recall product review
trigger_phrases:
  - 之前那个秘书方案评审
  - PRD 评审少了哪步
  - routine recall 方案
  - pensieve 下一步
cwd_hints:
  - C:\Users\hp\pensieve
  - C:\Users\hp\.claude\plans
checklist:
  - separate v0.1 scope from future phases
  - keep SessionEnd lightweight
  - use high-threshold low-token injection
  - add lifecycle reject supersede use_count
  - validate with real prompt regression
deliverables:
  - scoped PRD feedback
  - implementation priority list
  - next-step recommendation
tags:
  - prd
  - claude-code
  - routine
---
# Claude Code secretary PRD review routine

## When to use

Use when reviewing Pensieve / cc-secretary product plans, especially scope control, lifecycle management, hook safety, and progression from routine recall to skill promotion.

## Checklist

1. Separate immediate MVP scope from future automation.
2. Keep SessionEnd hooks lightweight; move extraction to offline scan.
3. Keep UserPromptSubmit injection high-threshold and under 150 tokens.
4. Add lifecycle primitives before promote-to-skill: reject, supersede, use_count.
5. Validate with real positive/negative prompt regression before adding Mem0 or MCP.
