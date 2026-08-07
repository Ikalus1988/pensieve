# Pensieve follow-up report

## What changed
- Added a migration path for legacy `routine_fts` tables so existing installs are rebuilt to `tokenize='trigram'`.
- Kept the YAML scalar→list parser fix.
- Kept generalized CJK matching and recall-routing improvements.
- Added regression coverage for:
  - trigram FTS rebuild migration
  - CJK query routing
  - scalar→list YAML transitions

## Evidence
- `pytest -q` -> 16 passed

## Next step
The open PR #3 is still dirty/out of date relative to `main`; it needs a rebase/merge from current `main` before it can be merged cleanly.
