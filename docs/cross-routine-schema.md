# Cross-routine Schema — federation + lesson linkage

> PR #6 / `feat/cross-routine-schema`  
> 本文档是 Pensieve frontmatter 的**新增 3 字段规范**,不改 `_LIST_KEYS` 之外的解析逻辑。

---

## 0. 为什么加这 3 个字段

Pensieve 仓目前 4 个 example routine 互相无关联,也没有指向 MisakaNet lesson 体系。  
当一个 routine 实际来源于某个 MisakaNet lesson 或上游仓 PR 时,我们没办法机器化地:

1. **追溯 routine 间关系**(`supersedes` / `superseded_by` / `related`)→ 影响 search ranking / lifecycle
2. **关联 MisakaNet lesson**(`lesson_links`)→ 让 LLM agent 知道 "这个 routine 来自哪条已沉淀经验"
3. **声明 federation 来源**(`federation`)→ 多个 MisakaNet 节点共享 routine 时,知道哪个仓是真主仓

3 字段统一为 `list[str]`,复用既有 `parse_simple_yaml` list 解析路径,**零新增解析逻辑**。

---

## 1. `references: list[str]`

跨 routine 关系。格式 `<rel>:<routine-id>`:

| Token                 | 语义                                                                |
|-----------------------|---------------------------------------------------------------------|
| `supersedes:<id>`     | 本 routine 替代旧 routine。索引时旧 routine 自动 `superseded`(v0.2+) |
| `superseded_by:<id>`  | 本 routine 已被新 routine 替代。搜索时本 card 不返回               |
| `related:<id>`        | 软关联 — search 结果附在 `additionalContext` 之后(>=0.5 score)    |

### v0.1 行为(本 PR 实现)

`references` 字段**只**存储与展示,**不影响** search / lifecycle。  
激活逻辑 (`supersedes` 自动 retire)留 v0.2 路线图 — 当前 PR 不改 `search()` / `reject_routine()` / `supersede_routine()` 行为。

### 示例(纯文档,**不**入 examples/ 索引)

```markdown
---
id: cross-routine-demo
title: Cross-routine schema demo
type: pipeline
status: active
confidence: verified
references:
  - superseded_by:fanuc-payload-pipeline-v2
  - related:cc-secretary-prd-review
  - related:misakanet-growth-review
---
```

> **注意**:本 demo **不**作为单独 routine card 放进 `examples/` —— 它只活在 `docs/cross-routine-schema.md` 文档里。`examples/` 里多塞一个 routine card 会偏移 bm25 语料统计,影响 `test_search.py` 阈值测试。

---

## 2. `lesson_links: list[str]`

MisakaNet lesson 路径引用。格式: `<path-from-MisakaNet-root>`。

Pensieve **不**主动 fetch — 消费方(LLM agent / CLI tool)需要自行 resolve。

| 约定路径                            | 含义                          |
|-------------------------------------|-------------------------------|
| `misakanet-50/lesson-NN-slug.md`    | 主 lessons/ 目录(2026-08-07 共 ~18 条) |
| `misakanet-zsxh/contrib/...md`      | 克莱恩 zsxh1990 分支上的 lessons |
| `misakanet/<org>/<repo>/lesson-...md` | 第三方 fork 的 lessons       |

### 示例

```markdown
lesson_links:
  - misakanet-50/lesson-12-recipe-vs-routine-distinction.md
  - misakanet-50/lesson-18-knowledge-bundle-self-reference-boundary.md
```

---

## 3. `federation: list[str]`

Provenance / lineage — 声明 routine 来自哪个 MisakaNet 节点 / 上游仓。

格式 `<key>:<value>`:

| Key                  | Value 形式                | 含义                                  |
|----------------------|---------------------------|---------------------------------------|
| `source_repo`        | `<owner>/<repo>`          | routine 首发仓                       |
| `contributed_via`    | `<owner>/<repo>#<pr-num>` | 把本 routine 带入本仓的 PR            |
| `absorbed_at`        | `YYYY-MM-DD`              | 本仓首次 `pensieve add` 的日期       |

### 示例

```markdown
federation:
  - source_repo: Ikalus1988/pensieve
  - contributed_via: zsxh1990/pensieve#6
  - absorbed_at: 2026-08-07
```

---

## 4. 实现细节(给 reviewer 看)

### 4.1 `routine.py` 改动

```diff
 _LIST_KEYS = {
     "aliases", "trigger_phrases", "cwd_hints", "checklist",
     "deliverables", "tags", "source_sessions",
+    "references", "lesson_links", "federation",
 }

 @dataclass
 class Routine:
     ...
     source_sessions: list[str] = field(default_factory=list)
+    references: list[str] = field(default_factory=list)
+    lesson_links: list[str] = field(default_factory=list)
+    federation: list[str] = field(default_factory=list)
     body: str = ""
     body_path: str = ""
```

`load_routine()` 调 `as_list()` 即可,无需新解析代码。  
`parse_simple_yaml` 不动 — 它已经在 `_LIST_KEYS` 命中时把 key 解析成 `list`。

### 4.2 兼容性

- 旧 routine card 没这 3 字段 → `as_list()` 返回 `[]`,默认值 `field(default_factory=list)`,**无回归**
- YAML 解析路径复用既有 `_LIST_KEYS` 集合 + 缩进 list 解析 + `[]` 内联 list 解析(PR #3 bugfix 也已覆盖 scalar→list 切换)

### 4.3 不在本次范围

- `search()` 用 `references` 提升排序 — **不做**(v0.2+ 路线)
- `supersede_routine()` 自动联动 `references` — **不做**(v0.2+ 路线)
- `install-hook` / `install-codex-hook` 读 `federation` — **不做**(v0.2+ 路线)

---

## 5. 下游联动

- **PR #4**(`docs/PR_MAKING.md`)— §3.2 frontmatter 表加 3 字段 + §6 lifecycle 加 references / federation 注意事项
- **PR #5**(`tests/test_hook_json_contract.py`)— 700-char 上限与新字段无关,但 `additionalContext` **不应该**塞 references(留 v0.2+)
- **PR #7**(`docs/ARCHITECTURE.md`)— 模块边界章节 link 本文档作为 frontmatter 扩展点的规范来源