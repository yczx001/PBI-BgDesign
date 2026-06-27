"""Compose multiple layers into a QGraphicsScene for preview."""
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem, QGraphicsPixmapItem
from PyQt6.QtCore import QRectF, QSize
from PyQt6.QtGui import QColor, QImage, QFont, QPixmap

from pbi_bgdesign.models import VisualObject
from pbi_bgdesign.layout_analyzer import LayoutAnalysis, classify_visual
from pbi_bgdesign.mock_renderer import render_mock_chart
from pbi_bgdesign.svg_design import parse_svg_to_items


class SceneBuilder:
    """Build a QGraphicsScene composing AI design, mock charts, and text layers."""

    def __init__(self, analysis: LayoutAnalysis):
        self.analysis = analysis
        self.page = analysis.page
        self.visibility: dict[str, bool] = {}
        self.svg_items: list = []  # AI-designed SVG items
        self._init_visibility()

    def _init_visibility(self):
        """Set default visibility based on classification."""
        for v in self.page.visuals:
            cat = self.analysis.classifications.get(v.id, "chart")
            # AI design items: visible by default
            # Text items: visible by default
            # Charts: visible in preview (mock), not exported
            self.visibility[v.id] = True

    def set_visible(self, visual_id: str, visible: bool):
        self.visibility[visual_id] = visible

    def set_svg_design(self, svg_code: str):
        """Set the AI-designed SVG background."""
        self.svg_items = parse_svg_to_items(svg_code)

    def build(self) -> QGraphicsScene:
        """Build the complete scene."""
        scene = QGraphicsScene()
        scene.setSceneRect(0, 0, self.page.width, self.page.height)
        scene.setBackgroundBrush(QColor("white"))

        # Layer 1: AI design SVG
        for item in self.svg_items:
            scene.addItem(item)

        # Layer 2: Original decorations and mock charts
        for v in self.page.visuals:
            if not self.visibility.get(v.id, True):
                continue

            cat = self.analysis.classifications.get(v.id, "chart")

            if cat == "decoration":
                self._add_decoration(scene, v)
            elif cat == "text":
                self._add_text(scene, v)
            elif cat == "chart":
                self._add_mock_chart(scene, v)
            elif cat == "interactive":
                self._add_interactive(scene, v)

        return scene

    def _add_decoration(self, scene: QGraphicsScene, v: VisualObject):
        """Add a decoration shape."""
        rect = QRectF(v.x, v.y, v.width, v.height)
        if v.visual_type == "shape":
            item = QGraphicsRectItem(rect)
            item.setBrush(QColor("#E8E8E8"))
            item.setPen(QColor("#CCCCCC"))
            scene.addItem(item)
        elif v.visual_type == "image" and v.resource_path:
            # Placeholder for image
            item = QGraphicsRectItem(rect)
            item.setBrush(QColor("#D4EDDA"))
            item.setPen(QColor("#28A745"))
            label = QGraphicsTextItem(f"[Image: {v.resource_path}]")
            label.setDefaultTextColor(QColor("#28A745"))
            label.setPos(v.x + 5, v.y + 5)
            scene.addItem(item)
            scene.addItem(label)

    def _add_text(self, scene: QGraphicsScene, v: VisualObject):
        """Add a text box."""
        text = v.title or "[Text]"
        item = QGraphicsTextItem(text)
        item.setDefaultTextColor(QColor("#333333"))
        item.setFont(QFont("Segoe UI", 12))
        item.setPos(v.x, v.y)
        scene.addItem(item)

    def _add_mock_chart(self, scene: QGraphicsScene, v: VisualObject):
        """Add a mock chart rendering."""
        w, h = int(v.width), int(v.height)
        if w <= 0 or h <= 0:
            return
        image = QImage(QSize(w, h), QImage.Format.Format_ARGB32)
        image.fill(0)
        render_mock_chart(v, image)
        pixmap = QPixmap.fromImage(image)
        item = QGraphicsPixmapItem(pixmap)
        item.setPos(v.x, v.y)
        scene.addItem(item)

    def _add_interactive(self, scene: QGraphicsScene, v: VisualObject):
        """Add an interactive element placeholder."""
        rect = QRectF(v.x, v.y, v.width, v.height)
        item = QGraphicsRectItem(rect)
        item.setBrush(QColor("#FFF3CD"))
        item.setPen(QColor("#FFC107"))
        scene.addItem(item)
