"""Main application window."""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QRadioButton, QButtonGroup,
    QPushButton, QLabel, QFileDialog, QToolBar, QStatusBar,
    QLineEdit, QTextEdit, QGroupBox,
)
from PyQt6.QtCore import Qt, QSize

from pbi_bgdesign.pbix_parser import parse_pbix
from pbi_bgdesign.layout_analyzer import analyze_layout
from pbi_bgdesign.renderer import SceneBuilder
from pbi_bgdesign.exporter import export_png, export_svg
from pbi_bgdesign.ui.canvas_widget import CanvasWidget
from pbi_bgdesign.ui.object_list import ObjectListWidget
from pbi_bgdesign.models import PbixData


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PBI-BgDesign")
        self.resize(1400, 900)

        self.pbix_data: PbixData | None = None
        self.current_page_index: int = 0
        self.scene_builder: SceneBuilder | None = None
        self._fullscreen = None

        self._setup_ui()

    def _setup_ui(self):
        # Toolbar
        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)

        self.btn_open = QPushButton("打开文件")
        self.btn_open.clicked.connect(self._open_file)
        toolbar.addWidget(self.btn_open)

        toolbar.addSeparator()

        self.page_combo = QLabel("当前页面: (未选择)")
        toolbar.addWidget(self.page_combo)

        toolbar.addSeparator()

        self.mode_group = QButtonGroup(self)
        self.radio_fixed = QRadioButton("固定")
        self.radio_flexible = QRadioButton("弹性")
        self.radio_free = QRadioButton("自由")
        self.radio_fixed.setChecked(True)
        self.mode_group.addButton(self.radio_fixed, 0)
        self.mode_group.addButton(self.radio_flexible, 1)
        self.mode_group.addButton(self.radio_free, 2)
        toolbar.addWidget(QLabel("布局模式:"))
        toolbar.addWidget(self.radio_fixed)
        toolbar.addWidget(self.radio_flexible)
        toolbar.addWidget(self.radio_free)

        toolbar.addSeparator()

        self.btn_ai = QPushButton("AI 设计")
        self.btn_ai.clicked.connect(self._start_ai_design)
        toolbar.addWidget(self.btn_ai)

        self.btn_fullscreen = QPushButton("全屏")
        self.btn_fullscreen.clicked.connect(self._toggle_fullscreen)
        toolbar.addWidget(self.btn_fullscreen)

        self.btn_export_png = QPushButton("导出 PNG")
        self.btn_export_png.clicked.connect(self._export_png)
        toolbar.addWidget(self.btn_export_png)

        self.btn_export_svg = QPushButton("导出 SVG")
        self.btn_export_svg.clicked.connect(self._export_svg)
        toolbar.addWidget(self.btn_export_svg)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Left: Page list
        self.page_list = QListWidget()
        self.page_list.setMaximumWidth(200)
        self.page_list.currentRowChanged.connect(self._on_page_selected)
        splitter.addWidget(self.page_list)

        # Center: Canvas + Object list
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)

        self.canvas = CanvasWidget()
        center_layout.addWidget(self.canvas, stretch=3)

        self.object_list = ObjectListWidget()
        self.object_list.visibility_changed.connect(self._on_visibility_changed)
        center_layout.addWidget(self.object_list, stretch=2)

        splitter.addWidget(center_widget)

        # Right: Chat panel
        self.chat_panel = QGroupBox("AI 对话")
        chat_layout = QVBoxLayout(self.chat_panel)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        chat_layout.addWidget(self.chat_display)

        input_layout = QHBoxLayout()
        self.btn_attach = QPushButton("附件")
        self.btn_attach.clicked.connect(self._attach_image)
        input_layout.addWidget(self.btn_attach)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("输入反馈...")
        self.chat_input.returnPressed.connect(self._send_chat)
        input_layout.addWidget(self.chat_input)

        self.btn_send = QPushButton("发送")
        self.btn_send.clicked.connect(self._send_chat)
        input_layout.addWidget(self.btn_send)

        chat_layout.addLayout(input_layout)
        self.chat_panel.setMaximumWidth(400)
        splitter.addWidget(self.chat_panel)

        splitter.setSizes([180, 800, 350])

        # Status bar
        self.statusBar().showMessage("就绪 -- 请打开 .pbix 文件")

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开 Power BI 文件", "", "Power BI 文件 (*.pbix);;所有文件 (*)"
        )
        if path:
            self.load_pbix(path)

    def load_pbix(self, path: str):
        try:
            self.pbix_data = parse_pbix(path)
            self.page_list.clear()
            for page in self.pbix_data.pages:
                self.page_list.addItem(QListWidgetItem(page.display_name))
            self.statusBar().showMessage(
                f"已加载: {path} -- {len(self.pbix_data.pages)} 页"
            )
            if self.page_list.count() > 0:
                self.page_list.setCurrentRow(0)
        except Exception as e:
            self.statusBar().showMessage(f"加载失败: {e}")

    def _on_page_selected(self, index: int):
        if not self.pbix_data or index < 0 or index >= len(self.pbix_data.pages):
            return
        self.current_page_index = index
        page = self.pbix_data.pages[index]
        analysis = analyze_layout(page)
        self.scene_builder = SceneBuilder(analysis)
        scene = self.scene_builder.build()
        self.canvas.set_scene(scene)
        self.object_list.load_analysis(analysis)
        self.page_combo.setText(f"当前页面: {page.display_name}")

    def _on_visibility_changed(self, visual_id: str, visible: bool):
        if self.scene_builder:
            self.scene_builder.set_visible(visual_id, visible)
            scene = self.scene_builder.build()
            self.canvas.set_scene(scene)

    def _get_mode(self) -> str:
        mode_id = self.mode_group.checkedId()
        return ["fixed", "flexible", "free"][mode_id]

    def _start_ai_design(self):
        self.chat_display.append("[AI 设计功能将在完成所有模块后启用]")

    def _send_chat(self):
        text = self.chat_input.text().strip()
        if text:
            self.chat_display.append(f"你: {text}")
            self.chat_input.clear()

    def _attach_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择参考图片", "", "图片 (*.png *.jpg *.jpeg *.svg);;所有文件 (*)"
        )
        if path:
            self.chat_display.append(f"已附加图片: {path}")

    def _toggle_fullscreen(self):
        from pbi_bgdesign.ui.fullscreen import FullscreenPreview
        if not self.pbix_data:
            return
        self._fullscreen = FullscreenPreview(
            total_pages=len(self.pbix_data.pages),
            current_page=self.current_page_index,
        )
        self._fullscreen.page_changed.connect(self._on_fullscreen_page_changed)
        self._fullscreen.closed.connect(self._on_fullscreen_closed)
        if self.scene_builder:
            self._fullscreen.set_scene(self.scene_builder.build())
        self._fullscreen.show()

    def _on_fullscreen_page_changed(self, index: int):
        self.current_page_index = index
        self.page_list.blockSignals(True)
        self.page_list.setCurrentRow(index)
        self.page_list.blockSignals(False)
        page = self.pbix_data.pages[index]
        analysis = analyze_layout(page)
        self.scene_builder = SceneBuilder(analysis)
        self._fullscreen.set_scene(self.scene_builder.build())

    def _on_fullscreen_closed(self):
        self._fullscreen = None

    def _export_png(self):
        if not self.scene_builder or not self.pbix_data:
            return
        page = self.pbix_data.pages[self.current_page_index]
        default_name = f"{page.display_name}_background.png"
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 PNG", default_name, "PNG 文件 (*.png)"
        )
        if path:
            scene = self.scene_builder.build()
            export_png(scene, path, QSize(int(page.width), int(page.height)))
            self.statusBar().showMessage(f"已导出: {path}")

    def _export_svg(self):
        if not self.scene_builder or not self.pbix_data:
            return
        page = self.pbix_data.pages[self.current_page_index]
        default_name = f"{page.display_name}_background.svg"
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 SVG", default_name, "SVG 文件 (*.svg)"
        )
        if path:
            scene = self.scene_builder.build()
            export_svg(scene, path, QSize(int(page.width), int(page.height)))
            self.statusBar().showMessage(f"已导出: {path}")
