# Task 10: Fullscreen Preview - Review

**Verdict:** NEEDS_FIX

**Date:** 2026-06-28

## Spec Compliance

| Requirement | Status | Notes |
|---|---|---|
| Frameless window | ✅ PASS | `Qt.WindowType.FramelessWindowHint` set (line 22) |
| Always-on-top | ✅ PASS | `Qt.WindowType.WindowStaysOnTopHint` set (line 22) |
| Uses CanvasWidget | ✅ PASS | `self.canvas = CanvasWidget()` (line 29) |
| Auto-hide control bar (3s) | ✅ PASS | `QTimer` with 3000ms interval (line 62) |
| Keyboard: ESC close | ✅ PASS | `Qt.Key.Key_Escape` → `self.close()` (line 96) |
| Keyboard: ← prev page | ✅ PASS | `Qt.Key.Key_Left` → `_prev_page()` (line 98) |
| Keyboard: → next page | ✅ PASS | `Qt.Key.Key_Right` → `_next_page()` (line 100) |
| Integrated into MainWindow | ✅ PASS | `_toggle_fullscreen()` creates and shows `FullscreenPreview` |

## Code Quality

### Positive Additions Beyond Spec

1. **`closeEvent` override** (lines 114-117): Properly stops timer and emits `closed` signal. Good cleanup practice, not in spec but valuable.
2. **`closed` signal**: Enables MainWindow to clean up its `_fullscreen` reference.
3. **`blockSignals` in `_on_fullscreen_page_changed`** (lines 213-215): Prevents circular updates between fullscreen and main window page lists — well-handled.
4. **`self.current_page_index` update** in `_on_fullscreen_page_changed` (line 212): Correctly uses existing attribute name rather than the spec's pseudo-code `self.current_page`.

### Bug Found

#### `mouseMoveEvent` will not fire without `setMouseTracking(True)`

**Severity:** Medium

The `mouseMoveEvent` override (line 110) is intended to show the control bar when the user moves the mouse. However, in Qt, `mouseMoveEvent` is only delivered without modifier buttons when `mouseTracking` is enabled. By default, `mouseTracking` is `False`, meaning `mouseMoveEvent` only fires while a mouse button is held down.

**Impact:** After the control bar auto-hides (3s), moving the mouse will NOT bring it back. The user would need to click-drag to trigger `mouseMoveEvent`. Keyboard shortcuts and button clicks still work, so this is not a complete blocker — but the "show controls on mouse movement" feature is broken.

**Fix:** Add `self.setMouseTracking(True)` in `__init__`, e.g. after line 23:

```python
self.setMouseTracking(True)
```

### Minor Observations (non-blocking)

1. **Visibility state not carried to fullscreen**: When fullscreen opens, `_toggle_fullscreen` passes `self.scene_builder.build()` which preserves the main window's visibility state. But when the user navigates pages in fullscreen, `_on_fullscreen_page_changed` creates a new `SceneBuilder` with all-default visibility. This means visibility toggles from the main window are lost after the first page switch. Minor UX issue — acceptable for now.

2. **Spec deviation in `_toggle_fullscreen`**: The spec uses `current_page=self.current_page` but the implementation uses `self.current_page_index`. This is the correct choice since `current_page_index` is the actual attribute name in MainWindow. The spec code was inconsistent with Task 9's implementation.

## Summary

The implementation is well-structured and closely follows the spec. The `closeEvent` addition and `blockSignals` usage show good engineering judgment. However, the missing `setMouseTracking(True)` means the mouse-move-to-show-controls feature is non-functional, which is a spec requirement. One small fix needed.

## Required Changes

1. Add `self.setMouseTracking(True)` to `FullscreenPreview.__init__` to enable `mouseMoveEvent` for showing controls on mouse hover.
