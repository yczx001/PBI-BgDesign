import pytest
import tempfile
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QGraphicsScene, QGraphicsRectItem
from PyQt6.QtCore import QSize, QRectF
from PyQt6.QtGui import QColor

from pbi_bgdesign.exporter import export_png, export_svg

app = QApplication.instance() or QApplication([])


@pytest.fixture
def sample_scene():
    scene = QGraphicsScene()
    scene.setSceneRect(0, 0, 1280, 720)
    scene.setBackgroundBrush(QColor("white"))
    # Add a rectangle
    item = QGraphicsRectItem(QRectF(100, 100, 300, 200))
    item.setBrush(QColor("#01B8AA"))
    scene.addItem(item)
    return scene


def test_export_png_creates_file(sample_scene, tmp_path):
    output = tmp_path / "test.png"
    export_png(sample_scene, str(output), QSize(1280, 720))
    assert output.exists()
    assert output.stat().st_size > 0


def test_export_svg_creates_file(sample_scene, tmp_path):
    output = tmp_path / "test.svg"
    export_svg(sample_scene, str(output), QSize(1280, 720))
    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert "<svg" in content
