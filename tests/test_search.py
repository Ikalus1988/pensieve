from pathlib import Path

from pensieve.store import connect, index_cards, search
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
