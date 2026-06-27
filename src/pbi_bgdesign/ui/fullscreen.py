"""Fullscreen preview window."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeyEvent

from pbi_bgdesign.ui.canvas_widget import CanvasWidget


class FullscreenPreview(QWidget):
    """Borderless fullscreen preview with auto-hide controls."""

    page_changed = pyqtSignal(int)  # New page index
    closed = pyqtSignal()

    def __init__(self, total_pages: int, current_page: int = 0, parent=None):
        super().__init__(parent)
        self.total_pages = total_pages
        self.current_page = current_page

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("background: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Canvas
        self.canvas = CanvasWidget()
        layout.addWidget(self.canvas, stretch=1)

        # Bottom control bar (auto-hide)
        self.control_bar = QWidget()
        self.control_bar.setStyleSheet("background: rgba(0,0,0,150);")
        self.control_bar.setFixedHeight(50)
        bar_layout = QHBoxLayout(self.control_bar)

        self.btn_prev = QPushButton("← 上一页")
        self.btn_prev.clicked.connect(self._prev_page)
        bar_layout.addWidget(self.btn_prev)

        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setStyleSheet("color: white; font-size: 14px;")
        bar_layout.addWidget(self.page_label)

        self.btn_next = QPushButton("下一页 →")
        self.btn_next.clicked.connect(self._next_page)
        bar_layout.addWidget(self.btn_next)

        bar_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding))

        self.btn_close = QPushButton("ESC 退出")
        self.btn_close.clicked.connect(self.close)
        bar_layout.addWidget(self.btn_close)

        layout.addWidget(self.control_bar)

        # Auto-hide timer
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(3000)
        self._hide_timer.timeout.connect(self._hide_controls)

        self._update_page_label()

    def set_scene(self, scene):
        self.canvas.set_scene(scene)
        self._show_controls()

    def _show_controls(self):
        self.control_bar.show()
        self._hide_timer.start()

    def _hide_controls(self):
        self.control_bar.hide()

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._update_page_label()
            self.page_changed.emit(self.current_page)
            self._show_controls()

    def _next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._update_page_label()
            self.page_changed.emit(self.current_page)
            self._show_controls()

    def _update_page_label(self):
        self.page_label.setText(f"第 {self.current_page + 1} / {self.total_pages} 页")

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_Left:
            self._prev_page()
        elif event.key() == Qt.Key.Key_Right:
            self._next_page()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.showFullScreen()
        self._show_controls()

    def mouseMoveEvent(self, event):
        self._show_controls()
        super().mouseMoveEvent(event)

    def closeEvent(self, event):
        self._hide_timer.stop()
        self.closed.emit()
        super().closeEvent(event)
