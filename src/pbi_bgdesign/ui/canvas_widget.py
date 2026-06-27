"""QGraphicsView widget for canvas preview with zoom and pan."""
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QPainter


class CanvasWidget(QGraphicsView):
    """Zoomable, pannable canvas view for previewing report designs."""

    visual_clicked = pyqtSignal(str)  # visual_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self._zoom_factor = 1.0

    def set_scene(self, scene: QGraphicsScene):
        self.setScene(scene)
        self.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom_factor = 1.0

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self._zoom_factor *= factor
            self.scale(factor, factor)
        else:
            super().wheelEvent(event)

    def fit_to_view(self):
        if self.scene():
            self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self._zoom_factor = 1.0
