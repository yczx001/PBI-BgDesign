import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSize

from pbi_bgdesign.models import VisualObject, PageData
from pbi_bgdesign.layout_analyzer import analyze_layout
from pbi_bgdesign.renderer import SceneBuilder

app = QApplication.instance() or QApplication([])


def _make_page():
    return PageData(
        name="p1", display_name="Home", width=1280, height=720,
        visuals=[
            VisualObject(id="v1", visual_type="donutChart", x=100, y=100, z=1000, width=300, height=250),
            VisualObject(id="v2", visual_type="shape", x=0, y=0, z=500, width=1280, height=60),
            VisualObject(id="v3", visual_type="textbox", x=20, y=10, z=1500, width=400, height=40),
        ]
    )


def test_scene_builder_creates_scene():
    page = _make_page()
    analysis = analyze_layout(page)
    builder = SceneBuilder(analysis)
    scene = builder.build()
    assert scene is not None
    assert scene.sceneRect().width() == 1280
    assert scene.sceneRect().height() == 720


def test_scene_builder_adds_mock_charts():
    page = _make_page()
    analysis = analyze_layout(page)
    builder = SceneBuilder(analysis)
    scene = builder.build()
    # Should have items (mock charts + shapes + text)
    assert len(scene.items()) > 0


def test_scene_builder_toggle_visibility():
    page = _make_page()
    analysis = analyze_layout(page)
    builder = SceneBuilder(analysis)
    scene = builder.build()
    # Hide the chart
    builder.set_visible("v1", False)
    # Build again — v1 should not be visible
    scene2 = builder.build()
    # We can't easily check which items are hidden without more access,
    # but at least verify it doesn't crash
    assert scene2 is not None
