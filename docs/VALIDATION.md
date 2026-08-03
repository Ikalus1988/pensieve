# v0.1.0 Validation Results

Date: 2026-08-03
Pensieve version: v0.1.0
Routine cards: 2 (fanuc-payload-pipeline, agently-mail-qq)

## Test Matrix

| # | Prompt | Type | Expected | Actual | Score | Injected Routine |
|---|--------|------|----------|--------|-------|-----------------|
| 1 | "之前那个流程" | 正例 (recall intent) | INJECT | ✅ INJECT | 0.77 | fanuc-payload-pipeline |
| 2 | "帮我从机器人备份提取payload" | 正例 (trigger match) | INJECT | ✅ INJECT | 0.77 | fanuc-payload-pipeline |
| 3 | "查收邮件" | 正例 (direct command) | INJECT | ✅ INJECT | 0.65 | agently-mail-qq |
| 4 | "帮我写 README" | 负例 | BLOCK | ✅ BLOCK | 0.30 | — |
| 5 | "分析 roadmap" | 负例 | BLOCK | ✅ BLOCK | 0.30 | — |
| 6 | "给 pensieve 加 MCP" | 负例 | BLOCK | ✅ BLOCK | 0.30 | — |

## Threshold Behavior

| Scenario | Score | Threshold | Inject? |
|----------|-------|-----------|---------|
| trigger + recall intent + cwd + confidence | 0.77 | 0.75 | ✅ |
| trigger + cwd + confidence (no recall) | 0.65 | 0.65 | ✅ |
| cwd + confidence only | 0.30 | 0.75 | ❌ |

## Known Limitations

- Single routine per injection (top-1 only)
- CJK FTS5 fallback scans full corpus (fine at <100 routines)
- No semantic similarity (BM25 + substring only)
- Manual routine card creation only (no auto-extraction yet)
