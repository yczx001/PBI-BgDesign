# Task 4 Report: SVG Parser + Exporter

## Status: DONE

## Commits
- `76776a20794e9d56acd3f5d5a7000dccea80f989` feat: add SVG parser and PNG/SVG exporter

## Test Results
Command: `py -m pytest tests/test_svg_design.py tests/test_exporter.py -v`
```
tests/test_svg_design.py::test_extract_svg_from_markdown_code_block PASSED
tests/test_svg_design.py::test_extract_svg_from_plain_text PASSED
tests/test_svg_design.py::test_extract_svg_returns_none_for_no_svg PASSED
tests/test_svg_design.py::test_parse_svg_to_items_returns_list PASSED
tests/test_exporter.py::test_export_png_creates_file PASSED
tests/test_exporter.py::test_export_svg_creates_file PASSED
6 passed in 0.27s
```

## Files Created
- `src/pbi_bgdesign/svg_design.py` — SVG parsing functions
- `src/pbi_bgdesign/exporter.py` — PNG/SVG export functions
- `tests/test_svg_design.py` — 4 tests for SVG parsing
- `tests/test_exporter.py` — 2 tests for PNG/SVG export

## Concerns
- Minor deviation from plan: `QGraphicsSvgItem` is in `PyQt6.QtSvgWidgets`, not `PyQt6.QtWidgets` (PyQt6 6.11). Fixed import accordingly.
