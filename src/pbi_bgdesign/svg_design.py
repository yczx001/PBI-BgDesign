"""Parse SVG code into QGraphicsItems for scene rendering."""
import re
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtSvgWidgets import QGraphicsSvgItem
from PyQt6.QtCore import QByteArray


def extract_svg_from_text(text: str) -> str | None:
    """Extract SVG code from AI response text.

    Looks for ```svg or ```xml code blocks first, then falls back to
    finding raw <svg>...</svg> tags.
    """
    # Try markdown code block
    pattern = r'```(?:svg|xml)\s*\n(.*?)```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try raw <svg> tag
    pattern = r'(<svg[^>]*>.*?</svg>)'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return None


def parse_svg_to_items(svg_code: str) -> list[QGraphicsSvgItem]:
    """Parse SVG code string into QGraphicsSvgItem list."""
    data = QByteArray(svg_code.encode("utf-8"))
    renderer = QSvgRenderer(data)
    if not renderer.isValid():
        return []

    item = QGraphicsSvgItem()
    item.setSharedRenderer(renderer)
    return [item]
