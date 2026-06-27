import json
import pytest
from unittest.mock import MagicMock, patch

from pbi_bgdesign.ai.designer import (
    AIDesigner,
    build_system_prompt,
    build_tool_definitions,
    SUPPORTED_VISION_MODELS,
)
from pbi_bgdesign.ai.skills import SkillLoader
from pbi_bgdesign.models import PageData, VisualObject
from pbi_bgdesign.layout_analyzer import analyze_layout


def test_build_system_prompt_contains_design_rules():
    prompt = build_system_prompt(skills_summary="No skills available.")
    assert "Power BI" in prompt
    assert "SVG" in prompt
    assert "设计规则" in prompt


def test_build_system_prompt_includes_skills():
    prompt = build_system_prompt(skills_summary="- frontend-designer: Expert designer")
    assert "frontend-designer" in prompt


def test_build_tool_definitions_has_required_tools():
    tools = build_tool_definitions()
    tool_names = {t["name"] for t in tools}
    assert "get_layout_info" in tool_names
    assert "apply_design" in tool_names
    assert "load_skill" in tool_names
    assert "list_skills" in tool_names


def test_supported_vision_models():
    assert "claude-sonnet-4-6" in SUPPORTED_VISION_MODELS
    assert "claude-opus-4" in SUPPORTED_VISION_MODELS


def test_ai_designer_model_supports_vision():
    designer = AIDesigner(api_key="test", model="claude-sonnet-4-6")
    assert designer.model_supports_vision() is True

    designer2 = AIDesigner(api_key="test", model="claude-3-haiku-20240307")
    assert designer2.model_supports_vision() is False


def test_ai_designer_build_messages_with_layout():
    page = PageData(name="p1", display_name="Home", width=1280, height=720, visuals=[])
    analysis = analyze_layout(page)
    designer = AIDesigner(api_key="test", model="claude-sonnet-4-6")
    designer.set_layout(analysis, "fixed")
    messages = designer._build_initial_messages()
    assert len(messages) > 0
    assert messages[0]["role"] == "user"
    assert "Home" in messages[0]["content"]
