import pytest

from pbi_bgdesign.models import VisualObject, PageData
from pbi_bgdesign.layout_analyzer import (
    classify_visual,
    detect_overlaps,
    analyze_layout,
    generate_layout_summary,
    OverlapGroup,
    LayoutAnalysis,
)


def _make_visual(id: str, vtype: str, x: float, y: float, w: float, h: float, z: int = 0) -> VisualObject:
    return VisualObject(id=id, visual_type=vtype, x=x, y=y, z=z, width=w, height=h)


def test_classify_visual_shape():
    assert classify_visual("shape") == "decoration"


def test_classify_visual_image():
    assert classify_visual("image") == "decoration"


def test_classify_visual_textbox():
    assert classify_visual("textbox") == "text"


def test_classify_visual_chart():
    assert classify_visual("donutChart") == "chart"
    assert classify_visual("lineChart") == "chart"
    assert classify_visual("tableEx") == "chart"
    assert classify_visual("slicer") == "chart"


def test_classify_visual_action_button():
    assert classify_visual("actionButton") == "interactive"


def test_detect_overlaps_no_overlap():
    v1 = _make_visual("a", "shape", 0, 0, 100, 100)
    v2 = _make_visual("b", "shape", 200, 200, 100, 100)
    groups = detect_overlaps([v1, v2])
    assert len(groups) == 2  # Each visual is its own group


def test_detect_overlaps_full_overlap():
    # v2 is completely inside v1
    v1 = _make_visual("a", "donutChart", 0, 0, 300, 300)
    v2 = _make_visual("b", "cardVisual", 50, 50, 100, 80)
    groups = detect_overlaps([v1, v2])
    assert len(groups) == 1
    assert len(groups[0].visuals) == 2


def test_detect_overlaps_transitive():
    # A overlaps B, B overlaps C → all in one group (transitive)
    # v1-v2 overlap: 80%, v2-v3 overlap: 60%, v1-v3 overlap: 40%
    # So v1-v3 don't directly overlap enough, but both overlap with v2 > 50%
    v1 = _make_visual("a", "shape", 0, 0, 100, 100)
    v2 = _make_visual("b", "shape", 20, 0, 100, 100)
    v3 = _make_visual("c", "shape", 60, 0, 100, 100)
    groups = detect_overlaps([v1, v2, v3])
    assert len(groups) == 1
    assert len(groups[0].visuals) == 3


def test_analyze_layout():
    page = PageData(
        name="p1", display_name="Home", width=1280, height=720,
        visuals=[
            _make_visual("v1", "donutChart", 100, 100, 300, 250),
            _make_visual("v2", "cardVisual", 150, 120, 100, 80),  # overlaps v1
            _make_visual("v3", "shape", 0, 0, 1280, 60),
            _make_visual("v4", "textbox", 20, 10, 400, 40),
        ]
    )
    result = analyze_layout(page)
    assert isinstance(result, LayoutAnalysis)
    assert len(result.groups) >= 2  # at least the overlap group + others
    assert result.page == page


def test_generate_layout_summary_contains_key_info():
    page = PageData(
        name="p1", display_name="Home", width=1280, height=720,
        visuals=[
            _make_visual("v1", "donutChart", 100, 100, 300, 250),
            _make_visual("v2", "shape", 0, 0, 1280, 60),
        ]
    )
    analysis = analyze_layout(page)
    summary = generate_layout_summary(analysis, "fixed")
    assert "1280" in summary
    assert "720" in summary
    assert "donutChart" in summary
    assert "shape" in summary
    assert "fixed" in summary.lower() or "固定" in summary
