"""Export QGraphicsScene to PNG or SVG files."""
from PyQt6.QtWidgets import QGraphicsScene
from PyQt6.QtCore import QSize, QRectF
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtSvg import QSvgGenerator


def export_png(scene: QGraphicsScene, path: str, size: QSize):
    """Export scene to PNG file at the given size."""
    image = QImage(size, QImage.Format.Format_ARGB32)
    image.fill(scene.backgroundBrush().color())
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scene.render(painter, QRectF(0, 0, size.width(), size.height()))
    painter.end()
    image.save(path, "PNG")


def export_svg(scene: QGraphicsScene, path: str, size: QSize):
    """Export scene to SVG file at the given size."""
    generator = QSvgGenerator()
    generator.setFileName(path)
    generator.setSize(size)
    generator.setViewBox(QRectF(0, 0, size.width(), size.height()))
    generator.setTitle("PBI-BgDesign Export")
    painter = QPainter(generator)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scene.render(painter, QRectF(0, 0, size.width(), size.height()))
    painter.end()
