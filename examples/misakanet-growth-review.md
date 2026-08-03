---
id: misakanet-growth-review
title: MisakaNet growth and release review routine
type: pipeline
status: active
confidence: observed
aliases:
  - MisakaNet 增长评审
  - roadmap review
  - release readiness
trigger_phrases:
  - 之前那个 MisakaNet 评审流程
  - 选下一步开源动作
  - roadmap 哪个优先
  - 质量复盘少了哪步
cwd_hints:
  - C:\Users\hp\MisakaNet
  - C:\Users\hp\Desktop\自研\misakanet
checklist:
  - inspect current repo state
  - compare docs roadmap issues and releases
  - identify stale notes
  - choose one concrete next action
  - write evidence-backed recommendation
deliverables:
  - prioritized next action
  - stale-or-current evidence
  - issue or PR recommendation
tags:
  - misakanet
  - growth
  - review
---
# MisakaNet growth and release review routine

## When to use

Use when the user asks what MisakaNet should do next, whether a note is stale, how to prioritize roadmap/release/frontend work, or why the previous review quality dropped.

## Checklist

1. Inspect the current repository state, not only old memory.
2. Compare README, ROADMAP, STATUS, issues, PR/release history, and local notes.
3. Mark stale notes explicitly when implementation already changed.
4. Pick one concrete next action instead of broad strategy.
5. Tie every recommendation to local or public evidence.
