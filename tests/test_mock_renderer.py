import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage
from PyQt6.QtCore import QSize

from pbi_bgdesign.models import VisualObject
from pbi_bgdesign.mock_renderer import (
    MOCK_COLORS,
    render_mock_chart,
    _deterministic_random,
    _extract_structure,
)


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for tests that need it."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_visual(vtype: str, x=0, y=0, w=300, h=200, z=0, config=None) -> VisualObject:
    return VisualObject(
        id=f"test_{vtype}", visual_type=vtype,
        x=x, y=y, z=z, width=w, height=h,
        config=config or {}
    )


def test_mock_colors_has_8_colors():
    assert len(MOCK_COLORS) == 8


def test_deterministic_random_same_seed():
    r1 = _deterministic_random("donutChart_page1", 5)
    r2 = _deterministic_random("donutChart_page1", 5)
    assert r1 == r2


def test_deterministic_random_different_seed():
    r1 = _deterministic_random("donutChart_page1", 5)
    r2 = _deterministic_random("lineChart_page2", 5)
    assert r1 != r2


def test_extract_structure_from_config():
    config = {
        "singleVisual": {
            "prototypeQuery": {
                "From": [{"Name": "t", "Entity": "Sales"}],
                "Select": [
                    {"Column": {"Name": "Category", "Property": "Category"}},
                    {"Measure": {"Name": "Amount", "Property": "Amount"}},
                    {"Measure": {"Name": "Count", "Property": "Count"}},
                ]
            }
        }
    }
    structure = _extract_structure(config)
    assert structure["categories"] == 1
    assert structure["measures"] == 2


def test_render_mock_donut_produces_image(qapp):
    visual = _make_visual("donutChart", w=300, h=250)
    image = QImage(QSize(300, 250), QImage.Format.Format_ARGB32)
    image.fill(0)
    render_mock_chart(visual, image)
    # Verify image is not all black (something was drawn)
    pixel = image.pixel(150, 125)
    assert pixel != 0


def test_render_mock_line_produces_image(qapp):
    visual = _make_visual("lineChart", w=400, h=200)
    image = QImage(QSize(400, 200), QImage.Format.Format_ARGB32)
    image.fill(0)
    render_mock_chart(visual, image)
    # Check that some pixels were drawn
    drawn = False
    for x in range(0, 400, 10):
        for y in range(0, 200, 10):
            if image.pixel(x, y) != 0:
                drawn = True
                break
        if drawn:
            break
    assert drawn


def test_render_mock_table_produces_image(qapp):
    visual = _make_visual("tableEx", w=500, h=300)
    image = QImage(QSize(500, 300), QImage.Format.Format_ARGB32)
    image.fill(0)
    render_mock_chart(visual, image)
    # Table should have drawn content
    pixel = image.pixel(10, 10)  # Header area
    assert pixel != 0


def test_render_mock_unknown_type_draws_placeholder(qapp):
    visual = _make_visual("unknownVisual", w=200, h=200)
    image = QImage(QSize(200, 200), QImage.Format.Format_ARGB32)
    image.fill(0)
    render_mock_chart(visual, image)
    # Should draw something (at minimum a gray rectangle)
    pixel = image.pixel(100, 100)
    assert pixel != 0
