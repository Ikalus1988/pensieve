# PR_MAKING — 贡献者指南

> 给 Pensieve 自己用的 PR 起草手册。  
> 适用场景:在 `Ikalus1988/pensieve` 提 PR 之前,自检 + 起草。

## 为什么需要这份文档

Pensieve 是一个 CLI / hook 库,**hook JSON 契约 + 阈值 + 生命周期**是它的"协议层"。  
改一个常量(例如 `AUTO_INJECT_THRESHOLD`)就可能让用户的 Claude Code / Codex CLI hook 静默失效。  
PR_MAKING 是给"提 PR 的人"的护栏:先把契约讲清,再让你动代码。

---

## 0. 准备:验证本地代码

提 PR 之前,本地必须能跑通 `tests/`。即使你只改文档:

```bash
cd ~/projects/pensieve
git checkout main && git pull --ff-only        # 对齐上游
python -m pip install -e .                      # 开发模式装包
python -m pytest -q                             # 期望 3 文件全过
```

如果 `pytest` 跑不通,**先修测试,再提 PR**。  
测试文件本身就是契约的一部分(详见 §3)。

---

## 1. 分支命名

| 类型 | 前缀 | 例 |
|---|---|---|
| 新功能 | `feat/` | `feat/cross-routine-schema` |
| Bug 修复 | `fix/` | `fix/yaml-scalar-list-append` |
| 文档 | `docs/` | `docs/pr-making-guide`(本 PR) |
| 架构 / 重构 | `arch/` | `arch/decouple-search-rank` |
| 测试 | `test/` | `test/hook-json-roundtrip` |

**禁止**:

- 用 `main` / `master` 直接 push
- 用中文 / emoji / 空格
- 在 `feat/` 分支里塞 `fix:` commit(另开 `fix/` 分支)

---

## 2. Commit 风格

参考现有 commit log(已 10+ 条,风格统一):

```
<type>: <一句话,中文/英文均可,祈使语气>
```

可选第二行写"为什么":

```
fix: threshold=0.65 from labeled test set, expanded CJK stopwords

The previous AUTO_INJECT=0.75 was too strict for routine cards without
recall-intent keywords. 0.65 catches "查收邮件" type direct commands.
```

**禁止**:

- 一个 commit 里改多个无关文件
- 把 merge commit 留在 PR(用 rebase)
- 引用 issue 用 `#123` 而不是 `fixes #123`(除非真的要 close)

---

## 3. 测试契约 — 改 hook / 阈值 / 协议必读

`tests/` 是 Pensieve 的"协议冻结"层。三个文件三种契约:

### 3.1 `test_search.py` — 阈值契约

| 测试函数 | 冻结的契约 |
|---|---|
| `test_search_cjk_recall_phrase` | 中文 recall 短语(`今天质量不行,少了哪一步?`)必须 ≥ 0.75 命中 fanuc |
| `test_hook_injects_high_confidence_match` | `hook_json` 输出必须含 `additionalContext` |
| `test_reject_excludes_from_search` | `reject_routine` 后,search 必须不再返回该 id |
| `test_supersede_excludes_from_search` | 同上,`supersede_routine` |
| `test_mark_used_increments_use_count` | `mark_used` 后 `use_count` +1 |
| `test_trigger_direct_command_injects_at_lower_threshold` | **trigger-only 命中走 0.65 阈值** |
| `test_trigger_direct_hook_increments_use_count` | `cli.main` hook 路径端到端 |

**改阈值必看**:动 `AUTO_INJECT_THRESHOLD` / `TRIGGER_DIRECT_THRESHOLD` / `CANDIDATE_THRESHOLD` 之前,先看 `test_search.py` 是否还过;过不了就**改测试**而不是删测试。  
测试是协议,不是参考实现。

### 3.2 `test_routine.py` — YAML frontmatter 契约

`routine.py` 的 `parse_simple_yaml` 是**故意不依赖 PyYAML** 的极简实现:

| 支持 | 不支持 |
|---|---|
| `key: scalar` | 嵌套字典 |
| `key: [a, b]` | 多行 list 末尾带注释 |
| 缩进 list `- item` | anchor / alias / 类型 tag |
| 标量→list 切换(`isinstance(existing, list)` 兜底,见 PR #3 bugfix) | 转义字符 |

新增 frontmatter 字段前,先确认 `routine.Routine` dataclass 加字段 + `parse_simple_yaml` 支持 + 测试覆盖。

### 3.3 `test_install.py` — hook 安装幂等性

两次 `_install_user_prompt_hook` 调用只产生 1 个 hook entry;  
保留 Codex 既有 `PreToolUse` / `TermCanvas` 等其它 hooks;  
写文件前先建 `.bak` 备份。

---

## 4. Hook JSON 契约 — 改 `hook.py` 必读

`hook_json(hits)` 输出必须严格符合 Claude Code / Codex CLI 期望:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "[Pensieve routine recall]\n..."
  }
}
```

**禁止**:

- 改 `hookEventName`(Agent 不会读)
- 改 `additionalContext` 字段名
- 输出多行 JSON / 带 `print` 噪音
- 改 `build_context` 里 `[Pensieve routine recall]` 前缀(Agent 用来识别来源)

**`additionalContext` 长度硬上限 700 字符**(`build_context` 默认参数)。  
超出会丢信息 — 改提示文案请先看 §6。

---

## 5. CJK 检索注意事项

`store.py` 默认用 SQLite `unicode61` 分词器,**不切 CJK**。  
PR #3 (`feat/cjk-search-support`) 加了 LIKE-based fallback 和 BM25 boost。

如果你的 PR 改 `search()` 评分逻辑:

1. 必须保留中文召回能跑(`test_search_cjk_recall_phrase` 还过)
2. 别加 PyTorch / sentence-transformers 依赖 — Pensieve MVP 是 stdlib + SQLite only
3. 阈值常量从 `CONFIDENCE_BOOST` 字典查,不要硬编码
4. 不要改 `routine_fts` 的 FTS5 schema(已有数据会失效)— 加辅助列可以

---

## 6. 生命周期命令(贡献者视图)

| 命令 | 用途 | 提 PR 时改动需注意 |
|---|---|---|
| `reject` | 标记误召回,排除 recall | 改 `persist_card=True` 默认值会让所有调用写卡文件 |
| `supersede` | 旧 routine 退役,引用新 id | `--by` 参数会写进 stdout 但不入库 |
| `stats` | 看 use_count / reject_count | 改字段名要同步 `test_search.py` |
| `install-hook` | Claude Code 装 `~/.claude/settings.json` | 改 `_install_user_prompt_hook` 之前跑 `test_install.py` |
| `install-codex-hook` | Codex CLI 装 `~/.codex/hooks.json` | 同上,且**不能改** `[hooks.state]` 信任哈希 |

---

## 7. PR 标题 / 描述模板

**标题** (`<type>: <一句话>`):

```
docs: add PR_MAKING contributor guide
fix: avoid scalar→list crash in parse_simple_yaml
feat: cross-routine dependency schema
```

**描述骨架**(中文/英文任选):

```markdown
## Problem
(用户视角:为什么需要改?哪条命令 / 哪条 hook 表现不对?)

## Changes
(代码视角:哪个文件、哪个函数、为什么这样改)
- `src/pensieve/store.py` — xxx
- `tests/test_search.py` — 加 xxx 断言

## Testing
(怎么验证:本地 pytest + 手工命令)

| 命令 | 期望 | 实际 |
|---|---|---|
| `pytest -q` | 8 passed | 8 passed |
| `pensieve hook "测试 prompt"` | `additionalContext` 含 fanuc | OK |
```

参考已有 PR:

- PR #3 `feat: CJK/Chinese search support + YAML parser bugfix` — 含 Problem / Changes / Testing 三段
- PR #2 `feat(hook): dual threshold for trigger-direct commands` — 含阈值表

---

## 8. 撞墙 / 自检清单(提 PR 前过一遍)

- [ ] `git status` 干净
- [ ] `git log origin/main..HEAD` 只看自己的 commit
- [ ] `python -m pytest -q` 全过
- [ ] `pensieve install-hook --dry-run` 输出符合预期
- [ ] `pensieve hook "真实 prompt"` 输出含 `additionalContext` 或 `{}`(不该有噪音)
- [ ] PR 标题 ≤ 70 字符,描述含 Problem / Changes / Testing
- [ ] 没在标题写 `[AI]` / `WIP` / `draft`(OpenClaw §6.1 守则,Pensieve 不一定但养成习惯)
- [ ] 没改无关文件(`git diff --stat origin/main`)
- [ ] 没在 commit message 提"AI 提的"

---

## 9. 关联文档

- `ARCHITECTURE.md` — 整体架构 / 数据流 / 模块边界(周末 PR #7)
- `CLAUDE_CODE_HOOK.md` — Claude Code 端 hook 安装
- `CODEX_HOOK.md` — Codex CLI 端 hook 安装
- `VALIDATION.md` — v0.1.0 实测矩阵(2 routine / 6 prompt / 阈值表)
- `PRD_NOTES.md` — 产品版本路线(v0.1 manual → v0.4 Mem0)