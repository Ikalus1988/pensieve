# Product notes

Pensieve MVP follows `C:\Users\hp\.claude\plans\cc-secretary-prd.md` with a reduced v0.1 scope:

- local routine cards first;
- SQLite FTS5 + substring fallback for CJK recall phrases;
- no SessionEnd extraction in v0.1;
- no Mem0 integration in v0.1;
- hook injection only on high-confidence matches.

## Version map

| Version | Scope |
| --- | --- |
| v0.1 | Manual cards, index/search/get/hook |
| v0.2 | Transcript queue + LLM extraction |
| v0.3 | promote-to-skill |
| v0.4 | Mem0 backend integration |
