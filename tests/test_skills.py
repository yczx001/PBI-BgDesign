import pytest
from pathlib import Path

from pbi_bgdesign.ai.skills import SkillLoader


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    d = tmp_path / "skills"
    d.mkdir()
    (d / "frontend-designer.md").write_text(
        "---\n"
        "name: frontend-designer\n"
        "description: Expert frontend designer\n"
        "whenToUse: When designing visual layouts\n"
        "---\n\n"
        "# Frontend Designer\n\n"
        "You are an expert frontend designer.\n"
    )
    (d / "data-viz.md").write_text(
        "---\n"
        "name: data-viz-expert\n"
        "description: Data visualization specialist\n"
        "whenToUse: When designing chart-heavy pages\n"
        "---\n\n"
        "# Data Viz Expert\n\n"
        "You specialize in data visualization.\n"
    )
    return d


def test_skill_loader_discovers_skills(skills_dir):
    loader = SkillLoader(str(skills_dir))
    loader.load()
    assert len(loader.skills) == 2
    names = {s["name"] for s in loader.skills}
    assert "frontend-designer" in names
    assert "data-viz-expert" in names


def test_skill_loader_get_summary(skills_dir):
    loader = SkillLoader(str(skills_dir))
    loader.load()
    summary = loader.get_summary()
    assert "frontend-designer" in summary
    assert "data-viz-expert" in summary
    assert "TRIGGER" in summary


def test_skill_loader_get_content(skills_dir):
    loader = SkillLoader(str(skills_dir))
    loader.load()
    content = loader.get_skill_content("frontend-designer")
    assert "expert frontend designer" in content


def test_skill_loader_missing_skill_returns_none(skills_dir):
    loader = SkillLoader(str(skills_dir))
    loader.load()
    assert loader.get_skill_content("nonexistent") is None


def test_skill_loader_empty_dir(tmp_path):
    d = tmp_path / "empty_skills"
    d.mkdir()
    loader = SkillLoader(str(d))
    loader.load()
    assert len(loader.skills) == 0
