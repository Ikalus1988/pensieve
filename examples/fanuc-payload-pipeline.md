---
id: fanuc-payload-pipeline
title: FANUC payload extraction pipeline
type: pipeline
status: active
confidence: verified
aliases:
  - 机器人备份提取
  - fanuc payload
  - sysvars.sv
  - 负载重心惯量
trigger_phrases:
  - 之前那个流程
  - 少了哪一步
  - 机器人备份提取payload
  - payload提取流程
cwd_hints:
  - C:\Users\hp
checklist:
  - locate sysvars.sv
  - parse PLST_GRP1
  - convert CG cm to m
  - convert inertia kg·cm² to kg·m²
  - generate Excel
  - self-check missing values and units
deliverables:
  - Excel payload table
  - unit conversion notes
  - anomaly report
tags:
  - fanuc
  - pipeline
  - payload
source_sessions:
  - claude --resume c0745421-2e3f-4912-afd5-622b4457fb0a
---
# FANUC payload extraction pipeline

## When to use

Use this routine when the user asks about FANUC robot backups, payload extraction, `sysvars.sv`, `PLST_GRP1`, mass, center of gravity, inertia, or complains that the previous standardized extraction workflow is missing a step.

## Checklist

1. Locate backup archives and extract them safely.
2. Find `sysvars.sv` case-insensitively in each robot backup.
3. Convert/read controller variables and parse `PLST_GRP1` payload records.
4. Extract mass, center of gravity, inertia, status, and robot identity fields.
5. Convert units: CG `cm -> m`; inertia `kg·cm² -> kg·m²`.
6. Generate the Excel deliverable with stable columns.
7. Self-check row counts, missing values, unit magnitude, and column order.

## Known traps

- CG is centimeters, not millimeters: `cm -> m` is `/100`.
- Inertia `kg·cm² -> kg·m²` is `/10000`.
- Do not trust a reference spreadsheet blindly; verify unit magnitudes.
