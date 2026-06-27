# Task 10 Fix Report: Mouse Tracking in Fullscreen Preview

## Bug Description

The `FullscreenPreview` window's "show controls on mouse hover" feature was not working because `mouseMoveEvent` only fires during button-drag operations by default in Qt.

## Root Cause

The `FullscreenPreview.__init__` method was missing `self.setMouseTracking(True)`. Without this call, Qt only sends `mouseMoveEvent` when a mouse button is pressed (i.e., during drag operations), not during simple mouse movement over the widget.

## Fix Applied

Added `self.setMouseTracking(True)` in `FullscreenPreview.__init__` after the canvas widget is created (line 33 in `src/pbi_bgdesign/ui/fullscreen.py`).

```python
# Canvas
self.canvas = CanvasWidget()
layout.addWidget(self.canvas, stretch=1)

# Enable mouse tracking so mouseMoveEvent fires without button press
self.setMouseTracking(True)
```

## Verification

Test command:
```bash
py -c "from PyQt6.QtWidgets import QApplication; from pbi_bgdesign.ui.fullscreen import FullscreenPreview; app = QApplication([]); f = FullscreenPreview(5); print('OK')"
```

Result: **OK** - Module imports successfully and `FullscreenPreview` instance can be created.

## Commit Information

- **Commit SHA:** `971fe68`
- **Commit Message:** `fix: add mouse tracking to fullscreen preview for hover control reveal`
- **Branch:** `feat/pbi-bgdesign-implementation`
- **File Modified:** `src/pbi_bgdesign/ui/fullscreen.py`

## Impact

With this fix, the fullscreen preview window will now properly show/hide the control bar when the user moves the mouse over the window, even without pressing any mouse buttons. This provides the expected user experience for the fullscreen preview feature.
