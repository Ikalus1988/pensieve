from pathlib import Path

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
    """Direct commands like '查收邮件' should inject at 0.65 threshold."""
    db = tmp_path / "pensieve.sqlite3"
    with connect(db) as conn:
        index_cards(conn, Path("examples"))
        # "sysvars.sv 提取" matches trigger but no recall intent keywords
        hits = search(conn, "sysvars.sv 提取", cwd="C:\\Users\\hp", limit=3)
    assert hits
    assert hits[0].score >= 0.65
    assert hits[0].score < 0.75
    # Verify trigger-only detection
    from pensieve.hook import _is_trigger_only
    assert _is_trigger_only(hits[0])
    # Should still inject due to lower threshold
    payload = hook_json(hits)
    assert "additionalContext" in payload
