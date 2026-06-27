"""Visual object list widget with checkboxes and grouping."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QHBoxLayout, QLabel,
)
from PyQt6.QtCore import Qt, pyqtSignal

from pbi_bgdesign.layout_analyzer import LayoutAnalysis, classify_visual


CATEGORY_LABELS = {
    "decoration": "[AI设计]",
    "text": "[文本]",
    "chart": "[图表]",
    "interactive": "[交互]",
}


class ObjectListWidget(QWidget):
    """Widget showing visual objects with checkboxes for export control."""

    visibility_changed = pyqtSignal(str, bool)  # visual_id, visible
    text_edited = pyqtSignal(str, str)  # visual_id, new_text

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.page_label = QLabel("当前页: (未选择)")
        layout.addWidget(self.page_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["导出", "类型", "名称", "位置/尺寸"])
        self.tree.setColumnWidth(0, 40)
        self.tree.setColumnWidth(1, 60)
        self.tree.setColumnWidth(2, 200)
        self.tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tree)

        btn_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("全选装饰")
        self.btn_select_none = QPushButton("全不选")
        self.btn_invert = QPushButton("反选")
        self.btn_select_all.clicked.connect(self._select_all_decorations)
        self.btn_select_none.clicked.connect(self._select_none)
        self.btn_invert.clicked.connect(self._invert_selection)
        btn_layout.addWidget(self.btn_select_all)
        btn_layout.addWidget(self.btn_select_none)
        btn_layout.addWidget(self.btn_invert)
        layout.addLayout(btn_layout)

        self._analysis: LayoutAnalysis | None = None

    def load_analysis(self, analysis: LayoutAnalysis):
        """Populate the tree from layout analysis."""
        self._analysis = analysis
        self.page_label.setText(f"当前页: {analysis.page.display_name}")
        self.tree.blockSignals(True)
        self.tree.clear()

        # Group visuals by overlap group
        visual_to_group = {}
        for g in analysis.groups:
            if len(g.visuals) > 1:
                for v in g.visuals:
                    visual_to_group[v.id] = g

        added = set()
        for g in analysis.groups:
            if len(g.visuals) > 1:
                group_item = QTreeWidgetItem()
                group_item.setText(2, f"[合成组 {g.id}] ({len(g.visuals)}个元素)")
                group_item.setExpanded(True)
                self.tree.addTopLevelItem(group_item)

                for v in g.visuals:
                    child = self._create_item(v, analysis)
                    group_item.addChild(child)
                    added.add(v.id)

        # Add ungrouped visuals
        for v in analysis.page.visuals:
            if v.id not in added:
                item = self._create_item(v, analysis)
                self.tree.addTopLevelItem(item)

        self.tree.blockSignals(False)

    def _create_item(self, v, analysis: LayoutAnalysis) -> QTreeWidgetItem:
        cat = analysis.classifications.get(v.id, "chart")
        label = CATEGORY_LABELS.get(cat, "[未知]")
        is_exportable = cat in ("decoration", "text") or v.title

        item = QTreeWidgetItem()
        item.setCheckState(0, Qt.CheckState.Checked if is_exportable else Qt.CheckState.Unchecked)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        if cat == "chart":
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        item.setText(1, label)
        name = v.title or v.visual_type
        item.setText(2, f"{name} ({v.id})")
        item.setText(3, f"x:{v.x:.0f} y:{v.y:.0f} w:{v.width:.0f} h:{v.height:.0f}")
        item.setData(0, Qt.ItemDataRole.UserRole, v.id)
        return item

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        if column == 0:
            vid = item.data(0, Qt.ItemDataRole.UserRole)
            if vid:
                checked = item.checkState(0) == Qt.CheckState.Checked
                self.visibility_changed.emit(vid, checked)

    def _select_all_decorations(self):
        self._set_all_check_states(lambda cat: cat in ("decoration", "text"))

    def _select_none(self):
        self._set_all_check_states(lambda cat: False)

    def _invert_selection(self):
        self.tree.blockSignals(True)
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            self._invert_item(item)
        self.tree.blockSignals(False)
        # Emit visibility for all items after inversion
        self._emit_all_visibility()

    def _invert_item(self, item: QTreeWidgetItem):
        if item.childCount() > 0:
            for i in range(item.childCount()):
                self._invert_item(item.child(i))
        else:
            current = item.checkState(0)
            item.setCheckState(0, Qt.CheckState.Unchecked if current == Qt.CheckState.Checked else Qt.CheckState.Checked)

    def _set_all_check_states(self, filter_fn):
        if not self._analysis:
            return
        self.tree.blockSignals(True)
        for i in range(self.tree.topLevelItemCount()):
            self._set_item_state(self.tree.topLevelItem(i), filter_fn)
        self.tree.blockSignals(False)
        self._emit_all_visibility()

    def _set_item_state(self, item: QTreeWidgetItem, filter_fn):
        if item.childCount() > 0:
            for i in range(item.childCount()):
                self._set_item_state(item.child(i), filter_fn)
        else:
            vid = item.data(0, Qt.ItemDataRole.UserRole)
            if vid and self._analysis:
                cat = self._analysis.classifications.get(vid, "chart")
                state = Qt.CheckState.Checked if filter_fn(cat) else Qt.CheckState.Unchecked
                item.setCheckState(0, state)

    def _emit_all_visibility(self):
        """Emit visibility_changed for all leaf items after bulk changes."""
        for i in range(self.tree.topLevelItemCount()):
            self._emit_item_visibility(self.tree.topLevelItem(i))

    def _emit_item_visibility(self, item: QTreeWidgetItem):
        if item.childCount() > 0:
            for i in range(item.childCount()):
                self._emit_item_visibility(item.child(i))
        else:
            vid = item.data(0, Qt.ItemDataRole.UserRole)
            if vid:
                checked = item.checkState(0) == Qt.CheckState.Checked
                self.visibility_changed.emit(vid, checked)
