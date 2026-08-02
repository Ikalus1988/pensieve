from pathlib import Path

from pensieve.routine import load_routine


def test_load_routine_frontmatter():
    routine = load_routine(Path("examples/fanuc-payload-pipeline.md"))
    assert routine.id == "fanuc-payload-pipeline"
    assert routine.status == "active"
    assert routine.confidence == "verified"
    assert "机器人备份提取" in routine.aliases
    assert "locate sysvars.sv" in routine.checklist
