# Task 1 Report: Project Setup + PBIX Parser

**Status:** DONE

## Summary

Task 1 completed successfully. All project scaffolding created, PBIX parser implemented and tested, real .pbix file parsed correctly.

## Files Created (14 files)

- `pyproject.toml` — project config (build backend changed from plan's `setuptools.backends._legacy:_Backend` to `setuptools.build_meta` for compatibility)
- `src/pbi_bgdesign/__init__.py` — empty
- `src/pbi_bgdesign/core/__init__.py` — empty
- `src/pbi_bgdesign/rendering/__init__.py` — empty
- `src/pbi_bgdesign/export/__init__.py` — empty
- `src/pbi_bgdesign/ai/__init__.py` — empty
- `src/pbi_bgdesign/ui/__init__.py` — empty
- `tests/__init__.py` — empty
- `src/pbi_bgdesign/models.py` — dataclasses (VisualObject, PageData, PbixData)
- `src/pbi_bgdesign/pbix_parser.py` — parser implementation
- `tests/test_pbix_parser.py` — 6 test functions
- `.gitignore` — exclude __pycache__, .egg-info, .pytest_cache, etc.

## Test Results

```
tests/test_pbix_parser.py::test_parse_pbix_returns_pbix_data PASSED
tests/test_pbix_parser.py::test_parse_pbix_extracts_pages PASSED
tests/test_pbix_parser.py::test_parse_pbix_extracts_visuals PASSED
tests/test_pbix_parser.py::test_parse_pbix_extracts_resources PASSED
tests/test_pbix_parser.py::test_parse_pbix_extracts_theme PASSED
tests/test_pbix_parser.py::test_parse_pbix_invalid_file PASSED

6 passed in 0.17s
```

## Real .pbix File Test

Successfully parsed `天津工厂新需求_V2.1 .pbix`:
- **17 pages** extracted with correct visual counts and dimensions
- **4 resources** extracted: 2 PNG images, 1 JSON config, 1 SVG
- **Theme** extracted: "Fluent 2 (Preview)" with full color palette

## Commits

- `ba89b99` — `feat: add PBIX parser with UTF-16-LE layout decoding and resource extraction`

## Concerns / Deviations

1. **build-backend changed**: Plan specified `setuptools.backends._legacy:_Backend` but this caused `ModuleNotFoundError: No module named 'setuptools.backends'` with the available setuptools version. Changed to standard `setuptools.build_meta`.

2. **Python environment**: The system has Anaconda3 Python 3.12.7 at `C:\ProgramData\anaconda3\python.exe`. The WindowsApps python.exe is a stub that doesn't work. `pip` command is not on PATH directly; must use `python -m pip`.

3. **pytest-qt DLL issue**: pytest-qt 4.5.0 fails to load with `ImportError: DLL load failed while importing QtCore` — likely missing Qt platform plugins. Uninstalled pytest-qt for now; parser tests don't need Qt. Will need to resolve for later tasks that test Qt components.

4. **Scripts installed to user site**: pip installed scripts to `C:\Users\rages\AppData\Roaming\Python\Python312\Scripts` (not on PATH). Not a blocker for testing.
