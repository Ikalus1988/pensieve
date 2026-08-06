# Pensieve update report

## What changed
- Added a reusable `agently-mail-qq` routine card for mail/support/Discord workflows.
- Generalized recall routing beyond the single mail case:
  - explicit recall signals: `查记忆`, `搜记忆`, `按例程`, `启动pensieve`, etc.
  - correction signals: `不要坚持己见`, `你有`, `别猜`, `别下结论`, etc.
  - trigger matching now also uses routine tags, not only aliases/trigger phrases.
  - Chinese punctuation is normalized before FTS query construction.
- Added top-k candidate context support in hooks for medium-confidence recall candidates, while still blocking weak/noisy matches.
- Added cross-scenario regression tests:
  - Glama/agently mail correction case routes to `agently-mail-qq`.
  - MisakaNet correction/recall case routes to `misakanet-growth-review`.
  - generic `搜记忆：帮我写 README` does not boost unrelated cwd-only hits.

## Why
The observed failure was a general routing failure: the assistant concluded tool capability before recalling relevant procedural memory. The fix is now pattern-based and applies to any routine with concrete cues, not only mail.

## Evidence
- `pytest -q` -> 13 passed

## Notes
This remains conservative: explicit recall/correction boosts only apply when the prompt also lexically matches a routine cue. CWD-only matches are not promoted into candidates.
