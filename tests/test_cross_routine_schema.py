"""Cross-routine schema freeze — references / lesson_links / federation.

These three frontmatter fields are added by PR #6. The tests below freeze
the *shape* of those fields (list[str], round-trip from YAML, default
empty list for legacy cards). They do NOT exercise any search/lifecycle
behavior yet — that activation is v0.2+ per docs/cross-routine-schema.md.
"""

from __future__ import annotations

from pathlib import Path

from pensieve.routine import _LIST_KEYS, Routine, load_routine, parse_simple_yaml


# --- helpers ---------------------------------------------------------------


def _write(tmp_path: Path, name: str, frontmatter: str) -> Path:
    p = tmp_path / name
    p.write_text(f"---\n{frontmatter}\n---\n# body\n", encoding="utf-8")
    return p


# --- 1. _LIST_KEYS registry ------------------------------------------------


def test_list_keys_contains_all_three_new_fields():
    """All three new fields must be registered in _LIST_KEYS for YAML list parsing."""
    assert "references" in _LIST_KEYS
    assert "lesson_links" in _LIST_KEYS
    assert "federation" in _LIST_KEYS


def test_list_keys_does_not_lose_legacy_fields():
    """Sanity: don't accidentally drop a legacy field when adding new ones."""
    legacy = {"aliases", "trigger_phrases", "cwd_hints", "checklist",
              "deliverables", "tags", "source_sessions"}
    assert legacy <= _LIST_KEYS


# --- 2. parse_simple_yaml shape contract ----------------------------------


def test_parse_simple_yaml_indented_list_for_references():
    """The indented-list form must produce a list of str (PR #3 scalar→list fix)."""
    text = (
        "id: x\n"
        "references:\n"
        "  - supersedes:a\n"
        "  - related:b\n"
    )
    meta = parse_simple_yaml(text)
    assert meta["references"] == ["supersedes:a", "related:b"]


def test_parse_simple_yaml_inline_list_for_lesson_links():
    """The inline [a, b] form must produce a list of str."""
    text = "lesson_links: [m1/l1.md, m1/l2.md]\n"
    meta = parse_simple_yaml(text)
    assert meta["lesson_links"] == ["m1/l1.md", "m1/l2.md"]


def test_parse_simple_yaml_inline_list_for_federation():
    text = 'federation: [source_repo: org/repo, contributed_via: org/repo#1]\n'
    meta = parse_simple_yaml(text)
    assert meta["federation"] == ["source_repo: org/repo", "contributed_via: org/repo#1"]


def test_parse_simple_yaml_missing_new_field_is_absent_not_present_as_empty():
    """parse_simple_yaml only writes a key when the frontmatter mentions it.

    A missing key is absent from the dict, not present as "" or [].
    The list-default is applied later by load_routine() via as_list(),
    not by parse_simple_yaml itself.
    """
    text = "id: x\n"
    meta = parse_simple_yaml(text)
    assert "references" not in meta
    assert "lesson_links" not in meta
    assert "federation" not in meta


def test_load_routine_applies_empty_list_default_for_missing_new_fields(tmp_path):
    """load_routine() must fill absent list fields with [] via as_list()."""
    p = _write(tmp_path, "demo.md",
        "id: demo\n"
        "title: Demo\n"
        "checklist:\n"
        "  - do thing\n"
    )
    r = load_routine(p)
    assert r.references == []
    assert r.lesson_links == []
    assert r.federation == []


def test_parse_simple_yaml_present_new_field_with_no_value_defaults_to_empty_list():
    """A _LIST_KEYS field written as `key:` with no value becomes []."""
    text = "id: x\nreferences:\nlesson_links:\nfederation:\n"
    meta = parse_simple_yaml(text)
    assert meta["references"] == []
    assert meta["lesson_links"] == []
    assert meta["federation"] == []


# --- 3. Routine dataclass defaults ----------------------------------------


def test_routine_dataclass_exposes_three_new_fields_as_list_str():
    """Bare Routine() must have all three new fields defaulting to []."""
    r = Routine(id="x", title="X")
    assert r.references == []
    assert r.lesson_links == []
    assert r.federation == []


def test_routine_dataclass_new_fields_default_factory_not_shared():
    """Two bare Routine() must not share the same default list (mutable-default trap)."""
    a = Routine(id="a", title="A")
    b = Routine(id="b", title="B")
    a.references.append("related:b")
    assert b.references == []   # not affected


# --- 4. load_routine end-to-end with synthetic fixtures --------------------


def test_load_routine_round_trips_references_field(tmp_path):
    p = _write(tmp_path, "demo.md",
        "id: demo\n"
        "title: Demo\n"
        "references:\n"
        "  - superseded_by:old-routine\n"
        "  - related:sibling-routine\n"
    )
    r = load_routine(p)
    assert r.references == ["superseded_by:old-routine", "related:sibling-routine"]


def test_load_routine_round_trips_lesson_links_field(tmp_path):
    p = _write(tmp_path, "demo.md",
        "id: demo\n"
        "title: Demo\n"
        "lesson_links:\n"
        "  - misakanet-50/lesson-1-foo.md\n"
        "  - misakanet-50/lesson-2-bar.md\n"
    )
    r = load_routine(p)
    assert r.lesson_links == ["misakanet-50/lesson-1-foo.md", "misakanet-50/lesson-2-bar.md"]


def test_load_routine_round_trips_federation_field(tmp_path):
    p = _write(tmp_path, "demo.md",
        "id: demo\n"
        "title: Demo\n"
        "federation:\n"
        "  - source_repo: Ikalus1988/pensieve\n"
        "  - contributed_via: zsxh1990/pensieve#6\n"
        "  - absorbed_at: 2026-08-07\n"
    )
    r = load_routine(p)
    assert r.federation == [
        "source_repo: Ikalus1988/pensieve",
        "contributed_via: zsxh1990/pensieve#6",
        "absorbed_at: 2026-08-07",
    ]


def test_load_routine_legacy_card_without_new_fields_still_loads(tmp_path):
    """A pre-PR-#6 card must continue to work — all three fields default to []."""
    p = _write(tmp_path, "legacy.md",
        "id: legacy\n"
        "title: Legacy\n"
        "checklist:\n"
        "  - do thing\n"
    )
    r = load_routine(p)
    assert r.id == "legacy"
    assert r.checklist == ["do thing"]
    assert r.references == []
    assert r.lesson_links == []
    assert r.federation == []


def test_load_routine_all_three_fields_together(tmp_path):
    """All three fields populated at once, mixed inline+indented forms."""
    p = _write(tmp_path, "full.md",
        "id: full\n"
        "title: Full\n"
        "references:\n"
        "  - related:other\n"
        "lesson_links: [m1/a.md, m1/b.md]\n"
        "federation: [source_repo: org/repo, absorbed_at: 2026-08-07]\n"
    )
    r = load_routine(p)
    assert r.references == ["related:other"]
    assert r.lesson_links == ["m1/a.md", "m1/b.md"]
    assert r.federation == ["source_repo: org/repo", "absorbed_at: 2026-08-07"]


# --- 5. Real example fixtures are unaffected ------------------------------


def test_real_examples_have_no_new_fields():
    """Existing examples/ cards must not have been mutated by PR #6.

    PR #6 is a pure-additive change; this test guards against accidental
    edits to legacy cards during the dataclass migration.
    """
    examples = Path("examples")
    if not examples.exists():
        pytest.skip("examples/ not present in this checkout")  # noqa: F821


def test_real_examples_load_with_empty_new_fields():
    """All real examples must continue to load with the new fields defaulting to []."""
    for path in sorted(Path("examples").glob("*.md")):
        r = load_routine(path)
        assert r.references == [], f"{path.name} leaked references: {r.references}"
        assert r.lesson_links == [], f"{path.name} leaked lesson_links: {r.lesson_links}"
        assert r.federation == [], f"{path.name} leaked federation: {r.federation}"