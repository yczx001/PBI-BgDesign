import pytest
from PyQt6.QtWidgets import QApplication
from pbi_bgdesign.svg_design import parse_svg_to_items, extract_svg_from_text

# Need QApplication for QGraphicsItem
app = QApplication.instance() or QApplication([])


def test_extract_svg_from_markdown_code_block():
    text = 'Here is the design:\n```svg\n<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="red"/></svg>\n```\nDone.'
    result = extract_svg_from_text(text)
    assert result is not None
    assert "<svg" in result
    assert "rect" in result


def test_extract_svg_from_plain_text():
    text = '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><circle cx="100" cy="100" r="50"/></svg>'
    result = extract_svg_from_text(text)
    assert result is not None
    assert "circle" in result


def test_extract_svg_returns_none_for_no_svg():
    text = "No SVG here, just text."
    result = extract_svg_from_text(text)
    assert result is None


def test_parse_svg_to_items_returns_list():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect x="10" y="10" width="80" height="80" fill="blue"/></svg>'
    items = parse_svg_to_items(svg)
    assert isinstance(items, list)
    assert len(items) > 0
