from pathlib import Path

from pensieve.routine import parse_simple_yaml
from pensieve.store import connect, index_cards, mark_used, reject_routine, search, stats, supersede_routine
from pensieve.hook import hook_json


def test_search_cjk_recall_phrase(tmp_path):
    db = tmp_path / "pensieve.sqlite3"
    with connect(db) as conn:
        count = index_cards(conn, Path("examples"))
        assert count >= 1
        hits = search(conn, "今天质量不行，少了哪一步？", cwd="C:\\Users\\hp", limit=3)
    assert hits
    assert hits[0].routine.id == "fanuc-payload-pipeline"
    assert hits[0].score >= 0.75


def test_cjk_query_hits_trigram_and_like_fallback(tmp_path):
    db = tmp_path / "pensieve.sqlite3"
    with connect(db) as conn:
        index_cards(conn, Path("examples"))
        hits = search(conn, "负载重心", cwd="C:\\Users\\hp", limit=3)
    assert hits
    assert hits[0].routine.id == "fanuc-payload-pipeline"
    assert hits[0].score >= 0.6


def test_init_db_rebuilds_non_trigram_fts(tmp_path):
    db = tmp_path / "pensieve.sqlite3"
    with connect(db) as conn:
        conn.execute(
            "CREATE VIRTUAL TABLE routine_fts USING fts5(id UNINDEXED, title, aliases, trigger_phrases, checklist, body)"
        )
        conn.commit()
        from pensieve.store import init_db

        init_db(conn)
        sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='routine_fts'"
        ).fetchone()[0]
    assert "trigram" in sql.lower()


def test_parse_simple_yaml_handles_scalar_then_list():
    parsed = parse_simple_yaml(
        """id: demo
aliases: primary
aliases:
  - fallback
"""
    )
    assert parsed["aliases"] == ["fallback"]


def test_hook_injects_high_confidence_match(tmp_path):
    db = tmp_path / "pensieve.sqlite3"
    with connect(db) as conn:
        index_cards(conn, Path("examples"))
        hits = search(conn, "之前那个机器人备份提取payload流程", cwd="C:\\Users\\hp", limit=3)
    payload = hook_json(hits)
    assert "additionalContext" in payload
    assert "fanuc-payload-pipeline" in payload


def test_reject_excludes_from_search(tmp_path):
    db = tmp_path / "pensieve.sqlite3"
    with connect(db) as conn:
        index_cards(conn, Path("examples"))
        rejected = reject_routine(conn, "fanuc-payload-pipeline")
        assert rejected is not None
        result = stats(conn, "fanuc-payload-pipeline")
        assert result == {"use_count": 0, "reject_count": 1}
        hits = search(conn, "之前那个机器人备份提取payload流程", cwd="C:\\Users\\hp", limit=3)
    assert all(h.routine.id != "fanuc-payload-pipeline" for h in hits)


def test_supersede_excludes_from_search(tmp_path):
    db = tmp_path / "pensieve.sqlite3"
    with connect(db) as conn:
        index_cards(conn, Path("examples"))
        superseded = supersede_routine(conn, "fanuc-payload-pipeline")
        assert superseded is not None
        hits = search(conn, "之前那个机器人备份提取payload流程", cwd="C:\\Users\\hp", limit=3)
    assert all(h.routine.id != "fanuc-payload-pipeline" for h in hits)


def test_mark_used_increments_use_count(tmp_path):
    db = tmp_path / "pensieve.sqlite3"
    with connect(db) as conn:
        index_cards(conn, Path("examples"))
        mark_used(conn, "fanuc-payload-pipeline")
        assert stats(conn, "fanuc-payload-pipeline") == {"use_count": 1, "reject_count": 0}


def test_trigger_direct_command_injects_at_lower_threshold(tmp_path):
    """Direct commands should still inject when trigger-only matches are strong enough."""
    db = tmp_path / "pensieve.sqlite3"
    with connect(db) as conn:
        index_cards(conn, Path("examples"))
        # "sysvars.sv 提取" matches trigger but no recall intent keywords
        hits = search(conn, "sysvars.sv 提取", cwd="C:\\Users\\hp", limit=3)
    assert hits
    assert hits[0].score >= 0.65
    # Verify trigger-only detection
    from pensieve.hook import _is_trigger_only
    assert _is_trigger_only(hits[0])
    # Should still inject due to lower threshold
    payload = hook_json(hits)
    assert "additionalContext" in payload


def test_trigger_direct_hook_increments_use_count(tmp_path):
    from pensieve.cli import main

    db = tmp_path / "pensieve.sqlite3"
    main(["--db", str(db), "--cards-dir", "examples", "index"])
    main(["--db", str(db), "hook", "sysvars.sv 提取", "--cwd", "C:\\Users\\hp"])
    with connect(db) as conn:
        assert stats(conn, "fanuc-payload-pipeline") == {"use_count": 1, "reject_count": 0}


def test_mail_recall_case_hits_agently_mail_routine(tmp_path):
    db = tmp_path / "pensieve.sqlite3"
    with connect(db) as conn:
        index_cards(conn, Path("examples"))
        hits = search(
            conn,
            "你有agently cli，你代劳。检查邮件收发记忆，不要坚持己见。",
            cwd="C:\\Users\\hp",
            limit=3,
        )
    assert hits
    assert hits[0].routine.id == "agently-mail-qq"
    assert hits[0].score >= 0.75
    payload = hook_json(hits)
    assert "agently-mail-qq" in payload


def test_correction_recall_generalizes_to_project_routine(tmp_path):
    db = tmp_path / "pensieve.sqlite3"
    with connect(db) as conn:
        index_cards(conn, Path("examples"))
        hits = search(
            conn,
            "查下记忆，MisakaNet roadmap 哪个优先，别猜。",
            cwd="C:\\Users\\hp\\MisakaNet",
            limit=3,
        )
    assert hits
    assert hits[0].routine.id == "misakanet-growth-review"
    assert "user correction" in hits[0].why
    assert "explicit recall request" in hits[0].why


def test_explicit_recall_does_not_boost_unrelated_cwd_only_hits(tmp_path):
    db = tmp_path / "pensieve.sqlite3"
    with connect(db) as conn:
        index_cards(conn, Path("examples"))
        hits = search(conn, "搜记忆：帮我写 README", cwd="C:\\Users\\hp", limit=5)
    assert hits
    assert all(
        "explicit recall request" not in h.why
        for h in hits
        if not any(w.startswith("trigger:") for w in h.why)
    )
    assert all(h.score < 0.55 for h in hits)
