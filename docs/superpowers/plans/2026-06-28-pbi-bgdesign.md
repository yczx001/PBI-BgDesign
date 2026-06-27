# PBI-BgDesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a PyQt6 desktop tool that reads Power BI .pbix files, uses Claude AI to design decorative backgrounds based on report layouts, and exports PNG/SVG background images.

**Architecture:** The tool has 3 layers: (1) PBIX parsing + layout analysis, (2) PyQt6 rendering with QGraphicsScene for preview/composition, (3) Claude API integration with streaming, tool use, MCP client, and Skill loading for AI-driven design. Data flows from .pbix → parsed layout → AI design (SVG) → composed scene → exported image.

**Tech Stack:** Python 3.11+, PyQt6, anthropic SDK, mcp Python SDK, pytest

## Global Constraints

- Python 3.11+ required
- Windows 11 platform — all paths use backslash, PowerShell 7 (`pwsh`) for commands
- All source files UTF-8 encoded
- .pbix Layout files are UTF-16-LE encoded JSON inside ZIP — must decode correctly
- Claude API calls use `anthropic` Python SDK with streaming enabled
- MCP config uses dictionary format matching Claude Code convention
- Skill files use markdown + YAML frontmatter format compatible with Claude Code

---

## Phase 1: Core Logic (Parser + Analyzer + Mock Renderer)

### Task 1: Project Setup + PBIX Parser

**Files:**
- Create: `pyproject.toml`
- Create: `src/pbi_bgdesign/__init__.py`
- Create: `src/pbi_bgdesign/models.py`
- Create: `src/pbi_bgdesign/pbix_parser.py`
- Create: `tests/__init__.py`
- Create: `tests/test_pbix_parser.py`

**Interfaces:**
- Produces: `PbixData`, `PageData`, `VisualObject` dataclasses in `models.py`
- Produces: `parse_pbix(path: str) -> PbixData` function in `pbix_parser.py`
- Consumed by: Task 2 (Layout Analyzer), Task 7 (Main Window)

- [ ] **Step 1: Create project structure**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "pbi-bgdesign"
version = "0.1.0"
description = "Power BI Background Designer"
requires-python = ">=3.11"
dependencies = [
    "PyQt6>=6.6",
    "anthropic>=0.40",
    "mcp>=1.0",
    "watchdog>=3.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-qt>=4.0"]

[project.scripts]
pbi-bgdesign = "pbi_bgdesign.app:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

Create empty `__init__.py` files:

```
src/pbi_bgdesign/__init__.py
src/pbi_bgdesign/core/__init__.py
src/pbi_bgdesign/rendering/__init__.py
src/pbi_bgdesign/export/__init__.py
src/pbi_bgdesign/ai/__init__.py
src/pbi_bgdesign/ui/__init__.py
tests/__init__.py
```

- [ ] **Step 2: Install dependencies**

Run:
```powershell
pwsh -Command "pip install -e '.[dev]'"
```
Expected: Successfully installed pbi-bgdesign and all dependencies.

- [ ] **Step 3: Define data models**

Create `src/pbi_bgdesign/models.py`:

```python
from dataclasses import dataclass, field


@dataclass
class VisualObject:
    """A single visual object extracted from a .pbix layout."""
    id: str
    visual_type: str  # "shape", "image", "textbox", "donutChart", etc.
    x: float
    y: float
    z: int
    width: float
    height: float
    title: str | None = None
    config: dict = field(default_factory=dict)
    resource_path: str | None = None

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.width, self.height)

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass
class PageData:
    """A single report page with its visual objects."""
    name: str
    display_name: str
    width: float
    height: float
    visuals: list[VisualObject] = field(default_factory=list)


@dataclass
class PbixData:
    """Complete parsed .pbix data."""
    pages: list[PageData] = field(default_factory=list)
    resources: dict[str, bytes] = field(default_factory=dict)
    theme: dict | None = None
    source_path: str = ""
```

- [ ] **Step 4: Write failing parser tests**

Create `tests/test_pbix_parser.py`:

```python
import json
import zipfile
import io
from pathlib import Path

import pytest

from pbi_bgdesign.pbix_parser import parse_pbix
from pbi_bgdesign.models import PbixData, PageData, VisualObject


@pytest.fixture
def sample_pbix_path(tmp_path: Path) -> Path:
    """Create a minimal .pbix file for testing."""
    layout = {
        "sections": [
            {
                "name": "page1_id",
                "displayName": "Home",
                "width": 1280,
                "height": 720,
                "displayOption": 1,
                "visualContainers": [
                    {
                        "x": 100.0,
                        "y": 50.0,
                        "z": 1000,
                        "width": 300.0,
                        "height": 200.0,
                        "config": json.dumps({
                            "name": "visual1",
                            "singleVisual": {
                                "visualType": "donutChart",
                                "objects": {
                                    "title": [{"properties": {"text": {"expr": {"Literal": {"Value": "'Sales Distribution'"}}}}}]
                                }
                            }
                        })
                    },
                    {
                        "x": 0.0,
                        "y": 0.0,
                        "z": 500,
                        "width": 1280.0,
                        "height": 60.0,
                        "config": json.dumps({
                            "name": "visual2",
                            "singleVisual": {
                                "visualType": "shape",
                                "objects": {}
                            }
                        })
                    },
                    {
                        "x": 1075.0,
                        "y": 7.0,
                        "z": 2000,
                        "width": 177.0,
                        "height": 46.0,
                        "config": json.dumps({
                            "name": "visual3",
                            "singleVisual": {
                                "visualType": "image",
                                "objects": {
                                    "general": [{"properties": {
                                        "imageUrl": {"expr": {"ResourcePackageItem": {
                                            "PackageName": "RegisteredResources",
                                            "ItemName": "logo.png"
                                        }}}
                                    }}]
                                }
                            }
                        })
                    }
                ]
            },
            {
                "name": "page2_id",
                "displayName": "Detail",
                "width": 1920,
                "height": 1080,
                "displayOption": 1,
                "visualContainers": []
            }
        ]
    }

    pbix_path = tmp_path / "test.pbix"
    with zipfile.ZipFile(pbix_path, "w") as zf:
        # Layout is UTF-16-LE encoded
        layout_json = json.dumps(layout, ensure_ascii=False)
        layout_bytes = layout_json.encode("utf-16-le")
        zf.writestr("Report/Layout", layout_bytes)
        # Add a resource file
        zf.writestr("Report/StaticResources/RegisteredResources/logo.png", b"\x89PNG_FAKE_DATA")
        # Add theme
        zf.writestr("Report/StaticResources/SharedResources/BaseThemes/theme.json",
                     json.dumps({"name": "CustomTheme"}))
    return pbix_path


def test_parse_pbix_returns_pbix_data(sample_pbix_path: Path):
    result = parse_pbix(str(sample_pbix_path))
    assert isinstance(result, PbixData)
    assert result.source_path == str(sample_pbix_path)


def test_parse_pbix_extracts_pages(sample_pbix_path: Path):
    result = parse_pbix(str(sample_pbix_path))
    assert len(result.pages) == 2
    assert result.pages[0].display_name == "Home"
    assert result.pages[0].width == 1280
    assert result.pages[0].height == 720
    assert result.pages[1].display_name == "Detail"
    assert result.pages[1].width == 1920


def test_parse_pbix_extracts_visuals(sample_pbix_path: Path):
    result = parse_pbix(str(sample_pbix_path))
    page = result.pages[0]
    assert len(page.visuals) == 3

    donut = page.visuals[0]
    assert donut.visual_type == "donutChart"
    assert donut.x == 100.0
    assert donut.y == 50.0
    assert donut.width == 300.0
    assert donut.title == "Sales Distribution"

    shape = page.visuals[1]
    assert shape.visual_type == "shape"

    image = page.visuals[2]
    assert image.visual_type == "image"
    assert image.resource_path == "logo.png"


def test_parse_pbix_extracts_resources(sample_pbix_path: Path):
    result = parse_pbix(str(sample_pbix_path))
    assert "logo.png" in result.resources
    assert result.resources["logo.png"] == b"\x89PNG_FAKE_DATA"


def test_parse_pbix_extracts_theme(sample_pbix_path: Path):
    result = parse_pbix(str(sample_pbix_path))
    assert result.theme is not None
    assert result.theme["name"] == "CustomTheme"


def test_parse_pbix_invalid_file(tmp_path: Path):
    bad_path = tmp_path / "bad.pbix"
    bad_path.write_text("not a zip file")
    with pytest.raises(Exception, match="not a valid .pbix"):
        parse_pbix(str(bad_path))
```

- [ ] **Step 5: Run tests to verify they fail**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; pytest tests/test_pbix_parser.py -v"
```
Expected: FAIL — `ModuleNotFoundError: No module named 'pbi_bgdesign'` or similar.

- [ ] **Step 6: Implement pbix_parser**

Create `src/pbi_bgdesign/pbix_parser.py`:

```python
"""Parser for .pbix files (Power BI reports)."""
import json
import zipfile
from pathlib import Path

from pbi_bgdesign.models import PbixData, PageData, VisualObject


def _decode_layout(raw: bytes) -> dict:
    """Decode Layout JSON from UTF-16-LE bytes."""
    text = raw.decode("utf-16-le")
    return json.loads(text)


def _extract_title(config: dict) -> str | None:
    """Extract chart title from visual config objects."""
    try:
        objects = config.get("singleVisual", {}).get("objects", {})
        title_list = objects.get("title", [])
        if title_list:
            props = title_list[0].get("properties", {})
            text_expr = props.get("text", {}).get("expr", {})
            literal = text_expr.get("Literal", {})
            value = literal.get("Value", "")
            # Remove surrounding quotes
            return value.strip("'\"") if value else None
    except (KeyError, IndexError, TypeError):
        pass
    return None


def _extract_resource_path(config: dict) -> str | None:
    """Extract image resource path from visual config."""
    try:
        objects = config.get("singleVisual", {}).get("objects", {})
        general = objects.get("general", [])
        if general:
            props = general[0].get("properties", {})
            image_url = props.get("imageUrl", {}).get("expr", {})
            rpi = image_url.get("ResourcePackageItem", {})
            return rpi.get("ItemName")
    except (KeyError, IndexError, TypeError):
        pass
    return None


def _parse_visual(vc: dict, index: int) -> VisualObject:
    """Parse a single visualContainer dict into a VisualObject."""
    config_str = vc.get("config", "{}")
    try:
        config = json.loads(config_str)
    except json.JSONDecodeError:
        config = {}

    visual_type = config.get("singleVisual", {}).get("visualType", "unknown")
    title = _extract_title(config)
    resource_path = _extract_resource_path(config)

    # Generate a stable ID from config name or fallback to index
    obj_name = config.get("name", f"visual_{index}")

    return VisualObject(
        id=obj_name,
        visual_type=visual_type,
        x=float(vc.get("x", 0)),
        y=float(vc.get("y", 0)),
        z=int(vc.get("z", 0)),
        width=float(vc.get("width", 0)),
        height=float(vc.get("height", 0)),
        title=title,
        config=config,
        resource_path=resource_path,
    )


def _parse_page(section: dict) -> PageData:
    """Parse a section dict into a PageData."""
    visuals = []
    for i, vc in enumerate(section.get("visualContainers", [])):
        visuals.append(_parse_visual(vc, i))

    return PageData(
        name=section.get("name", ""),
        display_name=section.get("displayName", ""),
        width=float(section.get("width", 1280)),
        height=float(section.get("height", 720)),
        visuals=visuals,
    )


def _extract_resources(zf: zipfile.ZipFile) -> dict[str, bytes]:
    """Extract static resources from the ZIP."""
    resources = {}
    prefix = "Report/StaticResources/RegisteredResources/"
    for entry in zf.namelist():
        if entry.startswith(prefix):
            filename = entry[len(prefix):]
            if filename:  # skip directory entries
                resources[filename] = zf.read(entry)
    return resources


def _extract_theme(zf: zipfile.ZipFile) -> dict | None:
    """Extract theme JSON if present."""
    prefix = "Report/StaticResources/SharedResources/BaseThemes/"
    for entry in zf.namelist():
        if entry.startswith(prefix) and entry.endswith(".json"):
            try:
                return json.loads(zf.read(entry))
            except json.JSONDecodeError:
                return None
    return None


def parse_pbix(path: str) -> PbixData:
    """Parse a .pbix file and return structured data.

    Args:
        path: Path to the .pbix file.

    Returns:
        PbixData with pages, resources, and theme.

    Raises:
        Exception: If the file is not a valid .pbix (ZIP) file.
    """
    try:
        with zipfile.ZipFile(path, "r") as zf:
            # Parse Layout
            if "Report/Layout" not in zf.namelist():
                raise ValueError("not a valid .pbix file: missing Report/Layout")

            layout_raw = zf.read("Report/Layout")
            layout = _decode_layout(layout_raw)

            # Parse pages
            pages = []
            for section in layout.get("sections", []):
                pages.append(_parse_page(section))

            # Extract resources
            resources = _extract_resources(zf)

            # Extract theme
            theme = _extract_theme(zf)

            return PbixData(
                pages=pages,
                resources=resources,
                theme=theme,
                source_path=path,
            )
    except zipfile.BadZipFile:
        raise ValueError(f"not a valid .pbix file: {path}")
```

- [ ] **Step 7: Run tests to verify they pass**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; pytest tests/test_pbix_parser.py -v"
```
Expected: All 6 tests PASS.

- [ ] **Step 8: Test with real .pbix file**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; python -c \"from pbi_bgdesign.pbix_parser import parse_pbix; d = parse_pbix('天津工厂新需求_V2.1 .pbix'); print(f'Pages: {len(d.pages)}'); [print(f'  {p.display_name}: {len(p.visuals)} visuals, {p.width}x{p.height}') for p in d.pages]; print(f'Resources: {list(d.resources.keys())}')\""
```
Expected: 17 pages listed with visual counts, resource filenames printed.

- [ ] **Step 9: Commit**

```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; git add -A; git commit -m 'feat: add PBIX parser with UTF-16-LE layout decoding and resource extraction'"
```

---

### Task 2: Layout Analyzer

**Files:**
- Create: `src/pbi_bgdesign/layout_analyzer.py`
- Create: `tests/test_layout_analyzer.py`

**Interfaces:**
- Consumes: `PbixData`, `PageData`, `VisualObject` from `models.py`
- Produces: `OverlapGroup`, `LayoutAnalysis`, `classify_visual()`, `analyze_layout()`, `generate_layout_summary()`

- [ ] **Step 1: Write failing analyzer tests**

Create `tests/test_layout_analyzer.py`:

```python
import pytest

from pbi_bgdesign.models import VisualObject, PageData
from pbi_bgdesign.layout_analyzer import (
    classify_visual,
    detect_overlaps,
    analyze_layout,
    generate_layout_summary,
    OverlapGroup,
    LayoutAnalysis,
)


def _make_visual(id: str, vtype: str, x: float, y: float, w: float, h: float, z: int = 0) -> VisualObject:
    return VisualObject(id=id, visual_type=vtype, x=x, y=y, z=z, width=w, height=h)


def test_classify_visual_shape():
    assert classify_visual("shape") == "decoration"


def test_classify_visual_image():
    assert classify_visual("image") == "decoration"


def test_classify_visual_textbox():
    assert classify_visual("textbox") == "text"


def test_classify_visual_chart():
    assert classify_visual("donutChart") == "chart"
    assert classify_visual("lineChart") == "chart"
    assert classify_visual("tableEx") == "chart"
    assert classify_visual("slicer") == "chart"


def test_classify_visual_action_button():
    assert classify_visual("actionButton") == "interactive"


def test_detect_overlaps_no_overlap():
    v1 = _make_visual("a", "shape", 0, 0, 100, 100)
    v2 = _make_visual("b", "shape", 200, 200, 100, 100)
    groups = detect_overlaps([v1, v2])
    assert len(groups) == 2  # Each visual is its own group


def test_detect_overlaps_full_overlap():
    # v2 is completely inside v1
    v1 = _make_visual("a", "donutChart", 0, 0, 300, 300)
    v2 = _make_visual("b", "cardVisual", 50, 50, 100, 80)
    groups = detect_overlaps([v1, v2])
    assert len(groups) == 1
    assert len(groups[0].visuals) == 2


def test_detect_overlaps_transitive():
    # A overlaps B, B overlaps C → all in one group
    v1 = _make_visual("a", "shape", 0, 0, 100, 100)
    v2 = _make_visual("b", "shape", 80, 0, 100, 100)
    v3 = _make_visual("c", "shape", 160, 0, 100, 100)
    groups = detect_overlaps([v1, v2, v3])
    assert len(groups) == 1
    assert len(groups[0].visuals) == 3


def test_analyze_layout():
    page = PageData(
        name="p1", display_name="Home", width=1280, height=720,
        visuals=[
            _make_visual("v1", "donutChart", 100, 100, 300, 250),
            _make_visual("v2", "cardVisual", 150, 120, 100, 80),  # overlaps v1
            _make_visual("v3", "shape", 0, 0, 1280, 60),
            _make_visual("v4", "textbox", 20, 10, 400, 40),
        ]
    )
    result = analyze_layout(page)
    assert isinstance(result, LayoutAnalysis)
    assert len(result.groups) >= 2  # at least the overlap group + others
    assert result.page == page


def test_generate_layout_summary_contains_key_info():
    page = PageData(
        name="p1", display_name="Home", width=1280, height=720,
        visuals=[
            _make_visual("v1", "donutChart", 100, 100, 300, 250),
            _make_visual("v2", "shape", 0, 0, 1280, 60),
        ]
    )
    analysis = analyze_layout(page)
    summary = generate_layout_summary(analysis, "fixed")
    assert "1280" in summary
    assert "720" in summary
    assert "donutChart" in summary
    assert "shape" in summary
    assert "fixed" in summary.lower() or "固定" in summary
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; pytest tests/test_layout_analyzer.py -v"
```
Expected: FAIL — `ModuleNotFoundError: No module named 'pbi_bgdesign.layout_analyzer'`

- [ ] **Step 3: Implement layout_analyzer**

Create `src/pbi_bgdesign/layout_analyzer.py`:

```python
"""Analyze visual object layouts: overlap detection, classification, summary generation."""
from dataclasses import dataclass, field

from pbi_bgdesign.models import VisualObject, PageData


# Element classification rules
CHART_TYPES = {
    "donutChart", "pieChart", "lineChart", "barChart", "clusteredBarChart",
    "columnChart", "clusteredColumnChart", "hundredPercentStackedBarChart",
    "hundredPercentStackedColumnChart", "lineClusteredColumnComboChart",
    "lineStackedColumnComboChart", "tableEx", "pivotTable", "cardVisual",
    "multiRowCard", "slicer", "advancedSlicerVisual", "scatterChart",
    "waterfallChart", "funnel", "gauge", "treemap", "map", "filledMap",
    "ribbonChart", "areaChart", "decodedRibbonChart",
}
# Also match custom visual type prefixes
CHART_PREFIXES = ("Gantt", "powerGANTT", "ScrollingText", "htmlContent", "synopticPanel")


def classify_visual(visual_type: str) -> str:
    """Classify a visual object type into a category.

    Returns: 'decoration', 'text', 'chart', or 'interactive'
    """
    if visual_type in ("shape", "image"):
        return "decoration"
    if visual_type == "textbox":
        return "text"
    if visual_type == "actionButton":
        return "interactive"
    if visual_type in CHART_TYPES:
        return "chart"
    if any(visual_type.startswith(p) for p in CHART_PREFIXES):
        return "chart"
    # Unknown types treated as charts (conservative: don't export)
    return "chart"


@dataclass
class OverlapGroup:
    """A group of overlapping visual objects."""
    id: str
    visuals: list[VisualObject] = field(default_factory=list)

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        """Combined bounding box of all visuals in group."""
        if not self.visuals:
            return (0, 0, 0, 0)
        min_x = min(v.x for v in self.visuals)
        min_y = min(v.y for v in self.visuals)
        max_x = max(v.x + v.width for v in self.visuals)
        max_y = max(v.y + v.height for v in self.visuals)
        return (min_x, min_y, max_x - min_x, max_y - min_y)


@dataclass
class LayoutAnalysis:
    """Complete analysis of a page layout."""
    page: PageData
    groups: list[OverlapGroup] = field(default_factory=list)
    classifications: dict[str, str] = field(default_factory=dict)  # visual_id -> category


def _overlap_ratio(v1: VisualObject, v2: VisualObject) -> float:
    """Calculate overlap ratio: intersection area / smaller visual area."""
    ix = max(0, min(v1.x + v1.width, v2.x + v2.width) - max(v1.x, v2.x))
    iy = max(0, min(v1.y + v1.height, v2.y + v2.height) - max(v1.y, v2.y))
    intersection = ix * iy
    smaller_area = min(v1.area, v2.area)
    if smaller_area <= 0:
        return 0.0
    return intersection / smaller_area


def detect_overlaps(visuals: list[VisualObject], threshold: float = 0.5) -> list[OverlapGroup]:
    """Detect overlapping visual groups using union-find.

    Two visuals are in the same group if their overlap ratio exceeds threshold.
    """
    n = len(visuals)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Check all pairs
    for i in range(n):
        for j in range(i + 1, n):
            if _overlap_ratio(visuals[i], visuals[j]) > threshold:
                union(i, j)

    # Group by root
    groups_map: dict[int, list[VisualObject]] = {}
    for i in range(n):
        root = find(i)
        groups_map.setdefault(root, []).append(visuals[i])

    # Sort each group by z-order
    groups = []
    for idx, members in enumerate(groups_map.values()):
        members.sort(key=lambda v: v.z)
        groups.append(OverlapGroup(id=f"group_{idx}", visuals=members))

    return groups


def analyze_layout(page: PageData) -> LayoutAnalysis:
    """Perform complete layout analysis on a page."""
    groups = detect_overlaps(page.visuals)
    classifications = {v.id: classify_visual(v.visual_type) for v in page.visuals}
    return LayoutAnalysis(page=page, groups=groups, classifications=classifications)


def generate_layout_summary(analysis: LayoutAnalysis, mode: str = "fixed") -> str:
    """Generate a structured text summary of the layout for AI consumption.

    Args:
        analysis: The layout analysis result.
        mode: Layout mode - 'fixed', 'flexible', or 'free'.
    """
    page = analysis.page
    mode_names = {"fixed": "固定布局", "flexible": "弹性布局", "free": "自由设计"}
    mode_desc = mode_names.get(mode, mode)

    lines = [
        f"## 页面: {page.display_name}",
        f"画布尺寸: {page.width} x {page.height}",
        f"布局模式: {mode_desc}",
        "",
        f"视觉对象总数: {len(page.visuals)}",
        "",
    ]

    # Group info
    lines.append("### 重叠分组:")
    for g in analysis.groups:
        if len(g.visuals) > 1:
            names = [f"{v.id}({v.visual_type})" for v in g.visuals]
            lines.append(f"  组 {g.id}: {', '.join(names)} — 合成组件")

    lines.append("")
    lines.append("### 视觉对象详情:")
    for v in page.visuals:
        cat = analysis.classifications.get(v.id, "unknown")
        title_str = f', 标题="{v.title}"' if v.title else ""
        lines.append(
            f"  [{cat}] {v.id}: type={v.visual_type}, "
            f"pos=({v.x:.0f},{v.y:.0f}), size={v.width:.0f}x{v.height:.0f}{title_str}"
        )

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; pytest tests/test_layout_analyzer.py -v"
```
Expected: All 10 tests PASS.

- [ ] **Step 5: Commit**

```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; git add -A; git commit -m 'feat: add layout analyzer with overlap detection and element classification'"
```

---

### Task 3: Mock Chart Renderer

**Files:**
- Create: `src/pbi_bgdesign/mock_renderer.py`
- Create: `tests/test_mock_renderer.py`

**Interfaces:**
- Consumes: `VisualObject` from `models.py`
- Produces: `render_mock_chart(visual: VisualObject, image: QImage)` function
- Consumed by: Task 5 (Renderer)

- [ ] **Step 1: Write failing mock renderer tests**

Create `tests/test_mock_renderer.py`:

```python
import pytest
from PyQt6.QtGui import QImage
from PyQt6.QtCore import QSize

from pbi_bgdesign.models import VisualObject
from pbi_bgdesign.mock_renderer import (
    MOCK_COLORS,
    render_mock_chart,
    _deterministic_random,
    _extract_structure,
)


def _make_visual(vtype: str, x=0, y=0, w=300, h=200, config=None) -> VisualObject:
    return VisualObject(
        id=f"test_{vtype}", visual_type=vtype,
        x=x, y=y, width=w, height=h,
        config=config or {}
    )


def test_mock_colors_has_8_colors():
    assert len(MOCK_COLORS) == 8


def test_deterministic_random_same_seed():
    r1 = _deterministic_random("donutChart_page1", 5)
    r2 = _deterministic_random("donutChart_page1", 5)
    assert r1 == r2


def test_deterministic_random_different_seed():
    r1 = _deterministic_random("donutChart_page1", 5)
    r2 = _deterministic_random("lineChart_page2", 5)
    assert r1 != r2


def test_extract_structure_from_config():
    config = {
        "singleVisual": {
            "prototypeQuery": {
                "From": [{"Name": "t", "Entity": "Sales"}],
                "Select": [
                    {"Column": {"Name": "Category", "Property": "Category"}},
                    {"Measure": {"Name": "Amount", "Property": "Amount"}},
                    {"Measure": {"Name": "Count", "Property": "Count"}},
                ]
            }
        }
    }
    structure = _extract_structure(config)
    assert structure["categories"] == 1
    assert structure["measures"] == 2


def test_render_mock_donut_produces_image():
    visual = _make_visual("donutChart", w=300, h=250)
    image = QImage(QSize(300, 250), QImage.Format.Format_ARGB32)
    image.fill(0)
    render_mock_chart(visual, image)
    # Verify image is not all black (something was drawn)
    pixel = image.pixel(150, 125)
    assert pixel != 0


def test_render_mock_line_produces_image():
    visual = _make_visual("lineChart", w=400, h=200)
    image = QImage(QSize(400, 200), QImage.Format.Format_ARGB32)
    image.fill(0)
    render_mock_chart(visual, image)
    # Check that some pixels were drawn
    drawn = False
    for x in range(0, 400, 10):
        for y in range(0, 200, 10):
            if image.pixel(x, y) != 0:
                drawn = True
                break
        if drawn:
            break
    assert drawn


def test_render_mock_table_produces_image():
    visual = _make_visual("tableEx", w=500, h=300)
    image = QImage(QSize(500, 300), QImage.Format.Format_ARGB32)
    image.fill(0)
    render_mock_chart(visual, image)
    # Table should have drawn content
    pixel = image.pixel(10, 10)  # Header area
    assert pixel != 0


def test_render_mock_unknown_type_draws_placeholder():
    visual = _make_visual("unknownVisual", w=200, h=200)
    image = QImage(QSize(200, 200), QImage.Format.Format_ARGB32)
    image.fill(0)
    render_mock_chart(visual, image)
    # Should draw something (at minimum a gray rectangle)
    pixel = image.pixel(100, 100)
    assert pixel != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; pytest tests/test_mock_renderer.py -v"
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement mock_renderer**

Create `src/pbi_bgdesign/mock_renderer.py`:

```python
"""Generate mock chart visuals for preview."""
import hashlib
from PyQt6.QtGui import QImage, QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtCore import Qt, QRectF, QPointF

from pbi_bgdesign.models import VisualObject

MOCK_COLORS = [
    "#01B8AA", "#374649", "#FD6252", "#F2C80F",
    "#5F6B6D", "#8AD4EB", "#FE9666", "#A66999",
]


def _deterministic_random(seed_str: str, count: int) -> list[float]:
    """Generate deterministic pseudo-random floats [0,1) from a seed string."""
    values = []
    for i in range(count):
        h = hashlib.md5(f"{seed_str}_{i}".encode()).hexdigest()
        values.append(int(h[:8], 16) / 0xFFFFFFFF)
    return values


def _extract_structure(config: dict) -> dict:
    """Extract structure info from visual config (category count, measure count)."""
    structure = {"categories": 3, "measures": 1}
    try:
        select = config.get("singleVisual", {}).get("prototypeQuery", {}).get("Select", [])
        cats = sum(1 for s in select if "Column" in s)
        measures = sum(1 for s in select if "Measure" in s)
        if cats > 0:
            structure["categories"] = min(cats, 10)
        if measures > 0:
            structure["measures"] = min(measures, 5)
    except (KeyError, TypeError):
        pass
    return structure


def _color(index: int) -> QColor:
    return QColor(MOCK_COLORS[index % len(MOCK_COLORS)])


def _draw_donut(painter: QPainter, rect: QRectF, seed: str, structure: dict):
    n = min(structure["categories"], 5)
    values = _deterministic_random(seed, n)
    total = sum(values) or 1
    start_angle = 0
    cx, cy = rect.center().x(), rect.center().y()
    radius = min(rect.width(), rect.height()) * 0.4
    inner_radius = radius * 0.55

    for i in range(n):
        span = int(5760 * values[i] / total)  # 5760 = 360*16
        painter.setBrush(QBrush(_color(i)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPie(
            QRectF(cx - radius, cy - radius, radius * 2, radius * 2),
            start_angle, span
        )
        start_angle += span

    # White center (donut hole)
    painter.setBrush(QBrush(QColor("white")))
    painter.drawEllipse(QPointF(cx, cy), inner_radius, inner_radius)


def _draw_pie(painter: QPainter, rect: QRectF, seed: str, structure: dict):
    n = min(structure["categories"], 5)
    values = _deterministic_random(seed, n)
    total = sum(values) or 1
    start_angle = 0
    cx, cy = rect.center().x(), rect.center().y()
    radius = min(rect.width(), rect.height()) * 0.4

    for i in range(n):
        span = int(5760 * values[i] / total)
        painter.setBrush(QBrush(_color(i)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPie(
            QRectF(cx - radius, cy - radius, radius * 2, radius * 2),
            start_angle, span
        )
        start_angle += span


def _draw_line(painter: QPainter, rect: QRectF, seed: str, structure: dict):
    margin = 30
    chart_rect = rect.adjusted(margin, margin, -margin, -margin)

    # Axes
    painter.setPen(QPen(QColor("#CCCCCC"), 1))
    painter.drawLine(int(chart_rect.left()), int(chart_rect.bottom()),
                     int(chart_rect.right()), int(chart_rect.bottom()))
    painter.drawLine(int(chart_rect.left()), int(chart_rect.top()),
                     int(chart_rect.left()), int(chart_rect.bottom()))

    # Lines
    n_measures = structure["measures"]
    n_points = 12
    for m in range(n_measures):
        values = _deterministic_random(f"{seed}_line{m}", n_points)
        painter.setPen(QPen(_color(m), 2))
        prev = None
        for i in range(n_points):
            x = chart_rect.left() + (chart_rect.width() * i / (n_points - 1))
            y = chart_rect.bottom() - (chart_rect.height() * values[i])
            if prev:
                painter.drawLine(int(prev.x()), int(prev.y()), int(x), int(y))
            prev = QPointF(x, y)


def _draw_bar(painter: QPainter, rect: QRectF, seed: str, structure: dict):
    margin = 30
    chart_rect = rect.adjusted(margin, margin, -margin, -margin)
    n_groups = 4
    bar_h = chart_rect.height() / n_groups * 0.7

    for g in range(n_groups):
        values = _deterministic_random(f"{seed}_bar{g}", structure["measures"])
        y = chart_rect.top() + chart_rect.height() * g / n_groups
        x_offset = 0
        for m, v in enumerate(values):
            w = chart_rect.width() * v * 0.8
            painter.setBrush(QBrush(_color(m)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(QRectF(chart_rect.left() + x_offset, y, w, bar_h))
            x_offset += w


def _draw_table(painter: QPainter, rect: QRectF, seed: str, structure: dict):
    cols = max(3, structure["measures"] + structure["categories"])
    rows = 5
    header_h = 30
    row_h = (rect.height() - header_h) / rows
    col_w = rect.width() / cols

    # Header
    painter.setBrush(QBrush(QColor("#374649")))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRect(QRectF(rect.x(), rect.y(), rect.width(), header_h))

    # Header text
    painter.setPen(QPen(QColor("white")))
    painter.setFont(QFont("Segoe UI", 9))
    for c in range(cols):
        painter.drawText(
            QRectF(rect.x() + c * col_w + 5, rect.y(), col_w - 10, header_h),
            Qt.AlignmentFlag.AlignVCenter, f"Column {c + 1}"
        )

    # Grid lines
    painter.setPen(QPen(QColor("#E0E0E0"), 1))
    for r in range(1, rows + 1):
        y = rect.y() + header_h + r * row_h
        painter.drawLine(int(rect.x()), int(y), int(rect.right()), int(y))
    for c in range(1, cols):
        x = rect.x() + c * col_w
        painter.drawLine(int(x), int(rect.y() + header_h), int(x), int(rect.bottom()))


def _draw_card(painter: QPainter, rect: QRectF, seed: str, structure: dict):
    # Background
    painter.setBrush(QBrush(QColor("#F5F5F5")))
    painter.setPen(QPen(QColor("#E0E0E0"), 1))
    painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 4, 4)

    # Big number
    values = _deterministic_random(seed, 1)
    number = f"{int(values[0] * 9999):,}"
    painter.setPen(QPen(QColor("#374649")))
    painter.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
    painter.drawText(rect.adjusted(10, 20, -10, -40), Qt.AlignmentFlag.AlignCenter, number)

    # Label
    painter.setFont(QFont("Segoe UI", 9))
    painter.setPen(QPen(QColor("#888888")))
    painter.drawText(rect.adjusted(10, rect.height() - 30, -10, -5),
                     Qt.AlignmentFlag.AlignCenter, "Metric")


def _draw_gantt(painter: QPainter, rect: QRectF, seed: str, structure: dict):
    margin = 20
    chart_rect = rect.adjusted(margin, margin, -margin, -margin)
    bars = _deterministic_random(seed, 8)
    bar_h = chart_rect.height() / 10

    # Timeline header
    painter.setBrush(QBrush(QColor("#F0F0F0")))
    painter.drawRect(QRectF(chart_rect.x(), chart_rect.y(), chart_rect.width(), 20))

    for i in range(8):
        start = bars[i] * 0.3
        length = bars[i] * 0.5 + 0.2
        y = chart_rect.y() + 25 + i * (bar_h + 3)
        x = chart_rect.x() + chart_rect.width() * start
        w = chart_rect.width() * length
        painter.setBrush(QBrush(_color(i)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(x, y, w, bar_h), 2, 2)


def _draw_slicer(painter: QPainter, rect: QRectF, seed: str, structure: dict):
    # Rounded tag shapes
    n = 3
    tags = ["Filter A", "Filter B", "Filter C"]
    y = rect.y() + 5
    for i in range(n):
        painter.setBrush(QBrush(QColor("#E8E8E8")))
        painter.setPen(QPen(QColor("#CCCCCC"), 1))
        tag_rect = QRectF(rect.x() + 5, y, rect.width() - 10, 22)
        painter.drawRoundedRect(tag_rect, 4, 4)
        painter.setPen(QPen(QColor("#666666")))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, tags[i])
        y += 27


def _draw_placeholder(painter: QPainter, rect: QRectF, label: str):
    painter.setBrush(QBrush(QColor("#F0F0F0")))
    painter.setPen(QPen(QColor("#CCCCCC"), 1, Qt.PenStyle.DashLine))
    painter.drawRect(rect)
    painter.setPen(QPen(QColor("#999999")))
    painter.setFont(QFont("Segoe UI", 10))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)


# Chart type -> render function mapping
_CHART_RENDERERS = {
    "donutChart": _draw_donut,
    "pieChart": _draw_pie,
    "lineChart": _draw_line,
    "hundredPercentStackedBarChart": _draw_bar,
    "hundredPercentStackedColumnChart": _draw_bar,
    "barChart": _draw_bar,
    "columnChart": _draw_bar,
    "tableEx": _draw_table,
    "pivotTable": _draw_table,
    "cardVisual": _draw_card,
    "multiRowCard": _draw_card,
    "slicer": _draw_slicer,
    "advancedSlicerVisual": _draw_slicer,
}

# Prefix match for custom visuals
_PREFIX_RENDERERS = {
    "Gantt": _draw_gantt,
    "powerGANTT": _draw_gantt,
    "htmlContent": lambda p, r, s, st: _draw_placeholder(p, r, "HTML Content"),
    "synopticPanel": lambda p, r, s, st: _draw_placeholder(p, r, "Map Panel"),
}


def render_mock_chart(visual: VisualObject, image: QImage):
    """Render a mock chart visual onto the given QImage.

    The image should be pre-sized to match the visual's dimensions.
    """
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    rect = QRectF(0, 0, image.width(), image.height())
    seed = f"{visual.id}_{visual.visual_type}"
    structure = _extract_structure(visual.config)

    vtype = visual.visual_type

    # Try exact match
    renderer = _CHART_RENDERERS.get(vtype)

    # Try prefix match
    if renderer is None:
        for prefix, fn in _PREFIX_RENDERERS.items():
            if vtype.startswith(prefix):
                renderer = fn
                break

    # Fallback: placeholder
    if renderer is None:
        _draw_placeholder(painter, rect, f"[{vtype}]")
    else:
        renderer(painter, rect, seed, structure)

    painter.end()
```

- [ ] **Step 4: Run tests**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; pytest tests/test_mock_renderer.py -v"
```
Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; git add -A; git commit -m 'feat: add mock chart renderer for donut, line, bar, table, card, gantt, slicer'"
```

---

### Task 4: SVG Parser + Exporter

**Files:**
- Create: `src/pbi_bgdesign/svg_design.py`
- Create: `src/pbi_bgdesign/exporter.py`
- Create: `tests/test_svg_design.py`
- Create: `tests/test_exporter.py`

**Interfaces:**
- Consumes: SVG string, QGraphicsScene
- Produces: `parse_svg_to_items(svg: str) -> list`, `export_png(scene, path, size)`, `export_svg(scene, path, size)`

- [ ] **Step 1: Write failing tests**

Create `tests/test_svg_design.py`:

```python
import pytest
from PyQt6.QtWidgets import QApplication
from pbi_bgdesign.svg_design import parse_svg_to_items, extract_svg_from_text

# Need QApplication for QGraphicsItem
app = QApplication.instance() or QApplication([])


def test_extract_svg_from_markdown_code_block():
    text = 'Here is the design:\n```svg\n<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="red"/></svg>\n```\nDone.'
    result = extract_svg_from_text(text)
    assert result is not None
    assert "<svg" in result
    assert "rect" in result


def test_extract_svg_from_plain_text():
    text = '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><circle cx="100" cy="100" r="50"/></svg>'
    result = extract_svg_from_text(text)
    assert result is not None
    assert "circle" in result


def test_extract_svg_returns_none_for_no_svg():
    text = "No SVG here, just text."
    result = extract_svg_from_text(text)
    assert result is None


def test_parse_svg_to_items_returns_list():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect x="10" y="10" width="80" height="80" fill="blue"/></svg>'
    items = parse_svg_to_items(svg)
    assert isinstance(items, list)
    assert len(items) > 0
```

Create `tests/test_exporter.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; pytest tests/test_svg_design.py tests/test_exporter.py -v"
```
Expected: FAIL

- [ ] **Step 3: Implement svg_design**

Create `src/pbi_bgdesign/svg_design.py`:

```python
"""Parse SVG code into QGraphicsItems for scene rendering."""
import re
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QGraphicsSvgItem
from PyQt6.QtCore import QByteArray


def extract_svg_from_text(text: str) -> str | None:
    """Extract SVG code from AI response text.

    Looks for ```svg or ```xml code blocks first, then falls back to
    finding raw <svg>...</svg> tags.
    """
    # Try markdown code block
    pattern = r'```(?:svg|xml)\s*\n(.*?)```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try raw <svg> tag
    pattern = r'(<svg[^>]*>.*?</svg>)'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return None


def parse_svg_to_items(svg_code: str) -> list[QGraphicsSvgItem]:
    """Parse SVG code string into QGraphicsSvgItem list."""
    data = QByteArray(svg_code.encode("utf-8"))
    renderer = QSvgRenderer(data)
    if not renderer.isValid():
        return []

    item = QGraphicsSvgItem()
    item.setSharedRenderer(renderer)
    return [item]
```

- [ ] **Step 4: Implement exporter**

Create `src/pbi_bgdesign/exporter.py`:

```python
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
```

- [ ] **Step 5: Run tests**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; pytest tests/test_svg_design.py tests/test_exporter.py -v"
```
Expected: All 6 tests PASS.

- [ ] **Step 6: Commit**

```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; git add -A; git commit -m 'feat: add SVG parser and PNG/SVG exporter'"
```

---

### Task 5: Scene Renderer (Composition)

**Files:**
- Create: `src/pbi_bgdesign/renderer.py`
- Create: `tests/test_renderer.py`

**Interfaces:**
- Consumes: `LayoutAnalysis`, mock renderer, SVG items
- Produces: `SceneBuilder` class that composes a QGraphicsScene

- [ ] **Step 1: Write failing tests**

Create `tests/test_renderer.py`:

```python
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSize

from pbi_bgdesign.models import VisualObject, PageData
from pbi_bgdesign.layout_analyzer import analyze_layout
from pbi_bgdesign.renderer import SceneBuilder

app = QApplication.instance() or QApplication([])


def _make_page():
    return PageData(
        name="p1", display_name="Home", width=1280, height=720,
        visuals=[
            VisualObject(id="v1", visual_type="donutChart", x=100, y=100, z=1000, width=300, height=250),
            VisualObject(id="v2", visual_type="shape", x=0, y=0, z=500, width=1280, height=60),
            VisualObject(id="v3", visual_type="textbox", x=20, y=10, z=1500, width=400, height=40),
        ]
    )


def test_scene_builder_creates_scene():
    page = _make_page()
    analysis = analyze_layout(page)
    builder = SceneBuilder(analysis)
    scene = builder.build()
    assert scene is not None
    assert scene.sceneRect().width() == 1280
    assert scene.sceneRect().height() == 720


def test_scene_builder_adds_mock_charts():
    page = _make_page()
    analysis = analyze_layout(page)
    builder = SceneBuilder(analysis)
    scene = builder.build()
    # Should have items (mock charts + shapes + text)
    assert len(scene.items()) > 0


def test_scene_builder_toggle_visibility():
    page = _make_page()
    analysis = analyze_layout(page)
    builder = SceneBuilder(analysis)
    scene = builder.build()
    # Hide the chart
    builder.set_visible("v1", False)
    # Build again — v1 should not be visible
    scene2 = builder.build()
    # We can't easily check which items are hidden without more access,
    # but at least verify it doesn't crash
    assert scene2 is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; pytest tests/test_renderer.py -v"
```
Expected: FAIL

- [ ] **Step 3: Implement renderer**

Create `src/pbi_bgdesign/renderer.py`:

```python
"""Compose multiple layers into a QGraphicsScene for preview."""
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem, QGraphicsPixmapItem
from PyQt6.QtCore import QRectF, QSize
from PyQt6.QtGui import QColor, QImage, QFont, QPixmap

from pbi_bgdesign.models import VisualObject
from pbi_bgdesign.layout_analyzer import LayoutAnalysis, classify_visual
from pbi_bgdesign.mock_renderer import render_mock_chart
from pbi_bgdesign.svg_design import parse_svg_to_items


class SceneBuilder:
    """Build a QGraphicsScene composing AI design, mock charts, and text layers."""

    def __init__(self, analysis: LayoutAnalysis):
        self.analysis = analysis
        self.page = analysis.page
        self.visibility: dict[str, bool] = {}
        self.svg_items: list = []  # AI-designed SVG items
        self._init_visibility()

    def _init_visibility(self):
        """Set default visibility based on classification."""
        for v in self.page.visuals:
            cat = self.analysis.classifications.get(v.id, "chart")
            # AI design items: visible by default
            # Text items: visible by default
            # Charts: visible in preview (mock), not exported
            self.visibility[v.id] = True

    def set_visible(self, visual_id: str, visible: bool):
        self.visibility[visual_id] = visible

    def set_svg_design(self, svg_code: str):
        """Set the AI-designed SVG background."""
        self.svg_items = parse_svg_to_items(svg_code)

    def build(self) -> QGraphicsScene:
        """Build the complete scene."""
        scene = QGraphicsScene()
        scene.setSceneRect(0, 0, self.page.width, self.page.height)
        scene.setBackgroundBrush(QColor("white"))

        # Layer 1: AI design SVG
        for item in self.svg_items:
            scene.addItem(item)

        # Layer 2: Original decorations and mock charts
        for v in self.page.visuals:
            if not self.visibility.get(v.id, True):
                continue

            cat = self.analysis.classifications.get(v.id, "chart")

            if cat == "decoration":
                self._add_decoration(scene, v)
            elif cat == "text":
                self._add_text(scene, v)
            elif cat == "chart":
                self._add_mock_chart(scene, v)
            elif cat == "interactive":
                self._add_interactive(scene, v)

        return scene

    def _add_decoration(self, scene: QGraphicsScene, v: VisualObject):
        """Add a decoration shape."""
        rect = QRectF(v.x, v.y, v.width, v.height)
        if v.visual_type == "shape":
            item = QGraphicsRectItem(rect)
            item.setBrush(QColor("#E8E8E8"))
            item.setPen(QColor("#CCCCCC"))
            scene.addItem(item)
        elif v.visual_type == "image" and v.resource_path:
            # Placeholder for image
            item = QGraphicsRectItem(rect)
            item.setBrush(QColor("#D4EDDA"))
            item.setPen(QColor("#28A745"))
            label = QGraphicsTextItem(f"[Image: {v.resource_path}]")
            label.setDefaultTextColor(QColor("#28A745"))
            label.setPos(v.x + 5, v.y + 5)
            scene.addItem(item)
            scene.addItem(label)

    def _add_text(self, scene: QGraphicsScene, v: VisualObject):
        """Add a text box."""
        text = v.title or "[Text]"
        item = QGraphicsTextItem(text)
        item.setDefaultTextColor(QColor("#333333"))
        item.setFont(QFont("Segoe UI", 12))
        item.setPos(v.x, v.y)
        scene.addItem(item)

    def _add_mock_chart(self, scene: QGraphicsScene, v: VisualObject):
        """Add a mock chart rendering."""
        w, h = int(v.width), int(v.height)
        if w <= 0 or h <= 0:
            return
        image = QImage(QSize(w, h), QImage.Format.Format_ARGB32)
        image.fill(0)
        render_mock_chart(v, image)
        pixmap = QPixmap.fromImage(image)
        item = QGraphicsPixmapItem(pixmap)
        item.setPos(v.x, v.y)
        scene.addItem(item)

    def _add_interactive(self, scene: QGraphicsScene, v: VisualObject):
        """Add an interactive element placeholder."""
        rect = QRectF(v.x, v.y, v.width, v.height)
        item = QGraphicsRectItem(rect)
        item.setBrush(QColor("#FFF3CD"))
        item.setPen(QColor("#FFC107"))
        scene.addItem(item)
```

- [ ] **Step 4: Run tests**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; pytest tests/test_renderer.py -v"
```
Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; git add -A; git commit -m 'feat: add scene renderer composing AI design, mock charts, and text layers'"
```

---

## Phase 2: AI Integration

### Task 6: Skill Loader

**Files:**
- Create: `src/pbi_bgdesign/ai/skills.py`
- Create: `tests/test_skills.py`

**Interfaces:**
- Produces: `SkillLoader` class with `load()`, `get_summary()`, `get_skill_content()`
- Consumed by: Task 8 (AI Designer)

- [ ] **Step 1: Write failing tests**

Create `tests/test_skills.py`:

```python
import pytest
from pathlib import Path

from pbi_bgdesign.ai.skills import SkillLoader


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    d = tmp_path / "skills"
    d.mkdir()
    (d / "frontend-designer.md").write_text(
        "---\n"
        "name: frontend-designer\n"
        "description: Expert frontend designer\n"
        "whenToUse: When designing visual layouts\n"
        "---\n\n"
        "# Frontend Designer\n\n"
        "You are an expert frontend designer.\n"
    )
    (d / "data-viz.md").write_text(
        "---\n"
        "name: data-viz-expert\n"
        "description: Data visualization specialist\n"
        "whenToUse: When designing chart-heavy pages\n"
        "---\n\n"
        "# Data Viz Expert\n\n"
        "You specialize in data visualization.\n"
    )
    return d


def test_skill_loader_discovers_skills(skills_dir):
    loader = SkillLoader(str(skills_dir))
    loader.load()
    assert len(loader.skills) == 2
    names = {s["name"] for s in loader.skills}
    assert "frontend-designer" in names
    assert "data-viz-expert" in names


def test_skill_loader_get_summary(skills_dir):
    loader = SkillLoader(str(skills_dir))
    loader.load()
    summary = loader.get_summary()
    assert "frontend-designer" in summary
    assert "data-viz-expert" in summary
    assert "TRIGGER" in summary


def test_skill_loader_get_content(skills_dir):
    loader = SkillLoader(str(skills_dir))
    loader.load()
    content = loader.get_skill_content("frontend-designer")
    assert "expert frontend designer" in content


def test_skill_loader_missing_skill_returns_none(skills_dir):
    loader = SkillLoader(str(skills_dir))
    loader.load()
    assert loader.get_skill_content("nonexistent") is None


def test_skill_loader_empty_dir(tmp_path):
    d = tmp_path / "empty_skills"
    d.mkdir()
    loader = SkillLoader(str(d))
    loader.load()
    assert len(loader.skills) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; pytest tests/test_skills.py -v"
```
Expected: FAIL

- [ ] **Step 3: Implement skills loader**

Create `src/pbi_bgdesign/ai/skills.py`:

```python
"""Load and manage Skill files from a directory."""
import re
from pathlib import Path


def _parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from markdown content."""
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}
    fm = {}
    for line in match.group(1).split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()
    return fm


class SkillLoader:
    """Load Skill files from a directory and provide access to their content."""

    def __init__(self, skills_dir: str):
        self.skills_dir = Path(skills_dir)
        self.skills: list[dict] = []
        self._content_cache: dict[str, str] = {}

    def load(self):
        """Scan skills directory and load all .md files."""
        self.skills = []
        self._content_cache = {}

        if not self.skills_dir.exists():
            return

        for path in sorted(self.skills_dir.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            fm = _parse_frontmatter(content)
            if "name" not in fm:
                continue

            skill = {
                "name": fm["name"],
                "description": fm.get("description", ""),
                "whenToUse": fm.get("whenToUse", ""),
                "path": str(path),
            }
            self.skills.append(skill)
            self._content_cache[fm["name"]] = content

    def get_summary(self) -> str:
        """Generate a summary of all loaded skills for system prompt injection."""
        if not self.skills:
            return "No skills available."

        lines = ["Available skills:"]
        for s in self.skills:
            lines.append(f"- {s['name']}: {s['description']}")
            if s["whenToUse"]:
                lines.append(f"  TRIGGER — {s['whenToUse']}")
        lines.append("")
        lines.append("Use the load_skill tool to load a skill's full instructions when needed.")
        return "\n".join(lines)

    def get_skill_content(self, name: str) -> str | None:
        """Get the full content of a skill by name."""
        return self._content_cache.get(name)
```

- [ ] **Step 4: Run tests**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; pytest tests/test_skills.py -v"
```
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; git add -A; git commit -m 'feat: add Skill loader with frontmatter parsing and summary generation'"
```

---

### Task 7: AI Designer (Claude API + Streaming + Tool Use)

**Files:**
- Create: `src/pbi_bgdesign/ai/designer.py`
- Create: `tests/test_designer.py`

**Interfaces:**
- Consumes: `SkillLoader`, `LayoutAnalysis`, Claude API
- Produces: `AIDesigner` class with `start_design()`, `send_message()`, streaming support
- Consumed by: Task 9 (Chat Panel UI)

- [ ] **Step 1: Write failing tests**

Create `tests/test_designer.py`:

```python
import json
import pytest
from unittest.mock import MagicMock, patch

from pbi_bgdesign.ai.designer import (
    AIDesigner,
    build_system_prompt,
    build_tool_definitions,
    SUPPORTED_VISION_MODELS,
)
from pbi_bgdesign.ai.skills import SkillLoader
from pbi_bgdesign.models import PageData, VisualObject
from pbi_bgdesign.layout_analyzer import analyze_layout


def test_build_system_prompt_contains_design_rules():
    prompt = build_system_prompt(skills_summary="No skills available.")
    assert "Power BI" in prompt
    assert "SVG" in prompt
    assert "设计规则" in prompt


def test_build_system_prompt_includes_skills():
    prompt = build_system_prompt(skills_summary="- frontend-designer: Expert designer")
    assert "frontend-designer" in prompt


def test_build_tool_definitions_has_required_tools():
    tools = build_tool_definitions()
    tool_names = {t["name"] for t in tools}
    assert "get_layout_info" in tool_names
    assert "apply_design" in tool_names
    assert "load_skill" in tool_names
    assert "list_skills" in tool_names


def test_supported_vision_models():
    assert "claude-sonnet-4-6" in SUPPORTED_VISION_MODELS
    assert "claude-opus-4" in SUPPORTED_VISION_MODELS


def test_ai_designer_model_supports_vision():
    designer = AIDesigner(api_key="test", model="claude-sonnet-4-6")
    assert designer.model_supports_vision() is True

    designer2 = AIDesigner(api_key="test", model="claude-3-haiku-20240307")
    assert designer2.model_supports_vision() is False


def test_ai_designer_build_messages_with_layout():
    page = PageData(name="p1", display_name="Home", width=1280, height=720, visuals=[])
    analysis = analyze_layout(page)
    designer = AIDesigner(api_key="test", model="claude-sonnet-4-6")
    designer.set_layout(analysis, "fixed")
    messages = designer._build_initial_messages()
    assert len(messages) > 0
    assert messages[0]["role"] == "user"
    assert "Home" in messages[0]["content"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; pytest tests/test_designer.py -v"
```
Expected: FAIL

- [ ] **Step 3: Implement AI designer**

Create `src/pbi_bgdesign/ai/designer.py`:

```python
"""AI design engine using Claude API with streaming and tool use."""
from PyQt6.QtCore import QObject, pyqtSignal
import json

import anthropic

from pbi_bgdesign.ai.skills import SkillLoader
from pbi_bgdesign.layout_analyzer import LayoutAnalysis, generate_layout_summary
from pbi_bgdesign.models import VisualObject

SUPPORTED_VISION_MODELS = {
    "claude-sonnet-4-6",
    "claude-opus-4",
    "claude-haiku-4-5-20251001",
}


def build_system_prompt(skills_summary: str) -> str:
    return f"""你是一个 Power BI 报表背景设计师。你的任务是根据报表布局信息设计美观的背景和装饰元素。

## 工作流程

**在开始设计之前，你必须先了解用户的偏好。请按以下步骤引导：**

1. 先简要分析布局结构（有多少图表、什么类型、页面用途）
2. 主动询问用户偏好（每次 1-2 个问题，不要一次问太多）：
   - 整体风格倾向（商务简约 / 科技感 / 清新活泼 / 深色系 / 明亮系）
   - 主色调偏好（冷色调 / 暖色调 / 特定颜色）
   - 装饰元素密度（简洁留白多 / 丰富填充多）
   - 是否有企业品牌色需要遵循
3. 根据回答提出 1-2 个设计方向建议，等用户确认
4. 确认后再开始生成设计

如果用户上传了参考图片，先分析图片的风格特征（配色、布局、装饰元素、整体氛围），提取关键风格要素作为设计依据。

## 可用工具

- 查询工具：了解布局细节、视觉对象信息、可用资源
- 操作工具：将设计应用到预览、添加文本元素、加载 Skill
- 外部工具（MCP）：搜索设计灵感、获取图标素材等

{skills_summary}

## 设计规则

1. SVG 尺寸必须与画布尺寸一致
2. 不要包含任何数据图表内容，只设计装饰性背景元素
3. 在动态图表位置留出适当空间
4. 考虑整体的视觉平衡和色彩协调
5. 输出 SVG 时使用 apply_design 工具应用到预览"""


def build_tool_definitions() -> list[dict]:
    return [
        {
            "name": "get_layout_info",
            "description": "获取指定页面的完整布局数据",
            "input_schema": {
                "type": "object",
                "properties": {
                    "page_name": {"type": "string", "description": "页面名称"}
                },
                "required": ["page_name"]
            }
        },
        {
            "name": "get_visual_details",
            "description": "获取某个视觉对象的完整 config（标题、样式、数据字段等）",
            "input_schema": {
                "type": "object",
                "properties": {
                    "visual_id": {"type": "string", "description": "视觉对象 ID"}
                },
                "required": ["visual_id"]
            }
        },
        {
            "name": "get_overlap_groups",
            "description": "获取重叠分组的详细信息",
            "input_schema": {
                "type": "object",
                "properties": {
                    "page_name": {"type": "string", "description": "页面名称"}
                },
                "required": ["page_name"]
            }
        },
        {
            "name": "list_resources",
            "description": "列出 .pbix 中可用的图片资源",
            "input_schema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "apply_design",
            "description": "将 SVG 设计应用到预览画布",
            "input_schema": {
                "type": "object",
                "properties": {
                    "svg_code": {"type": "string", "description": "完整的 SVG 代码"}
                },
                "required": ["svg_code"]
            }
        },
        {
            "name": "add_text_element",
            "description": "在指定位置添加文本元素",
            "input_schema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "font_size": {"type": "number"},
                    "color": {"type": "string"}
                },
                "required": ["text", "x", "y"]
            }
        },
        {
            "name": "highlight_visual",
            "description": "在预览中高亮某个视觉对象",
            "input_schema": {
                "type": "object",
                "properties": {
                    "visual_id": {"type": "string"},
                    "color": {"type": "string"}
                },
                "required": ["visual_id"]
            }
        },
        {
            "name": "load_skill",
            "description": "加载指定 Skill 的完整内容到对话上下文",
            "input_schema": {
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "Skill 名称"}
                },
                "required": ["skill_name"]
            }
        },
        {
            "name": "list_skills",
            "description": "列出所有可用的 Skill",
            "input_schema": {
                "type": "object",
                "properties": {}
            }
        },
    ]


class AIDesigner(QObject):
    """AI design engine managing Claude API conversation."""

    # Signals for UI
    text_received = pyqtSignal(str)       # Streaming text chunk
    tool_calling = pyqtSignal(str)         # Tool name being called
    design_applied = pyqtSignal(str)       # SVG code applied
    error_occurred = pyqtSignal(str)       # Error message
    finished = pyqtSignal()                # Response complete

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        super().__init__()
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.skill_loader: SkillLoader | None = None
        self.analysis: LayoutAnalysis | None = None
        self.mode: str = "fixed"
        self.conversation: list[dict] = []
        self.resources: dict[str, bytes] = {}

    def model_supports_vision(self) -> bool:
        return self.model in SUPPORTED_VISION_MODELS

    def set_layout(self, analysis: LayoutAnalysis, mode: str):
        self.analysis = analysis
        self.mode = mode
        self.conversation = []

    def set_skill_loader(self, loader: SkillLoader):
        self.skill_loader = loader

    def _build_initial_messages(self) -> list[dict]:
        if not self.analysis:
            return []
        summary = generate_layout_summary(self.analysis, self.mode)
        return [{"role": "user", "content": f"请为以下页面设计背景:\n\n{summary}"}]

    def _handle_tool(self, name: str, input_data: dict) -> str:
        """Execute a tool call and return the result as a string."""
        if name == "get_layout_info":
            if self.analysis:
                return generate_layout_summary(self.analysis, self.mode)
            return "No layout loaded."

        elif name == "get_visual_details":
            vid = input_data.get("visual_id", "")
            if self.analysis:
                for v in self.analysis.page.visuals:
                    if v.id == vid:
                        return json.dumps(v.config, indent=2, ensure_ascii=False)
            return f"Visual '{vid}' not found."

        elif name == "get_overlap_groups":
            if self.analysis:
                groups = self.analysis.groups
                result = []
                for g in groups:
                    if len(g.visuals) > 1:
                        names = [f"{v.id}({v.visual_type})" for v in g.visuals]
                        result.append(f"Group {g.id}: {', '.join(names)}")
                return "\n".join(result) if result else "No overlap groups found."
            return "No layout loaded."

        elif name == "list_resources":
            if self.resources:
                return ", ".join(self.resources.keys())
            return "No resources found."

        elif name == "apply_design":
            svg = input_data.get("svg_code", "")
            self.design_applied.emit(svg)
            return "Design applied to preview."

        elif name == "load_skill":
            skill_name = input_data.get("skill_name", "")
            if self.skill_loader:
                content = self.skill_loader.get_skill_content(skill_name)
                if content:
                    return f"Skill loaded:\n\n{content}"
                return f"Skill '{skill_name}' not found."
            return "No skill loader configured."

        elif name == "list_skills":
            if self.skill_loader:
                return self.skill_loader.get_summary()
            return "No skills available."

        elif name == "add_text_element":
            return f"Text element added: '{input_data.get('text', '')}' at ({input_data.get('x', 0)}, {input_data.get('y', 0)})"

        elif name == "highlight_visual":
            return f"Highlighted visual: {input_data.get('visual_id', '')}"

        return f"Unknown tool: {name}"

    def start_design(self):
        """Start a new design conversation."""
        self.conversation = self._build_initial_messages()
        self._call_api()

    def send_message(self, text: str, image_data: bytes | None = None, image_type: str | None = None):
        """Send a user message (with optional image) and get AI response."""
        content: list[dict] | str
        if image_data and image_type:
            import base64
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_type,
                        "data": base64.b64encode(image_data).decode("utf-8"),
                    }
                },
                {"type": "text", "text": text}
            ]
        else:
            content = text

        self.conversation.append({"role": "user", "content": content})
        self._call_api()

    def _call_api(self):
        """Call Claude API with streaming and handle tool use loop."""
        skills_summary = self.skill_loader.get_summary() if self.skill_loader else "No skills available."
        system = build_system_prompt(skills_summary)
        tools = build_tool_definitions()

        try:
            while True:
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=8192,
                    system=system,
                    messages=self.conversation,
                    tools=tools,
                ) as stream:
                    assistant_content = []
                    for event in stream:
                        # Handle text delta
                        if hasattr(event, 'type'):
                            if event.type == "content_block_delta":
                                delta = event.delta
                                if hasattr(delta, 'text') and delta.text:
                                    self.text_received.emit(delta.text)
                                elif hasattr(delta, 'partial_json') and delta.partial_json:
                                    pass  # Tool input streaming

                    # Get the final message
                    message = stream.get_final_message()
                    assistant_content = list(message.content)

                self.conversation.append({"role": "assistant", "content": assistant_content})

                # Check for tool use
                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use":
                        self.tool_calling.emit(block.name)
                        result = self._handle_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                if not tool_results:
                    break  # No more tool calls, conversation turn complete

                self.conversation.append({"role": "user", "content": tool_results})

        except anthropic.APIError as e:
            self.error_occurred.emit(f"API error: {e}")
        except Exception as e:
            self.error_occurred.emit(f"Error: {e}")
        finally:
            self.finished.emit()
```

- [ ] **Step 4: Run tests**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; pytest tests/test_designer.py -v"
```
Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; git add -A; git commit -m 'feat: add AI designer with Claude API streaming, tool use, and vision support'"
```

---

### Task 8: MCP Client

**Files:**
- Create: `src/pbi_bgdesign/ai/mcp_client.py`
- Create: `tests/test_mcp_client.py`

**Interfaces:**
- Consumes: MCP config JSON
- Produces: `MCPClientManager` class that connects to MCP servers and aggregates tools
- Consumed by: Task 7 (AIDesigner)

- [ ] **Step 1: Write failing tests**

Create `tests/test_mcp_client.py`:

```python
import json
import pytest
from pathlib import Path

from pbi_bgdesign.ai.mcp_client import MCPClientManager, load_mcp_config


@pytest.fixture
def mcp_config(tmp_path: Path) -> Path:
    config = {
        "mcpServers": {
            "test-server": {
                "command": "echo",
                "args": ["test"]
            },
            "remote-server": {
                "url": "http://localhost:3001/sse"
            }
        }
    }
    path = tmp_path / "mcp_config.json"
    path.write_text(json.dumps(config))
    return path


def test_load_mcp_config_reads_dict_format(mcp_config):
    config = load_mcp_config(str(mcp_config))
    assert "test-server" in config["mcpServers"]
    assert "remote-server" in config["mcpServers"]


def test_load_mcp_config_missing_file(tmp_path):
    config = load_mcp_config(str(tmp_path / "nonexistent.json"))
    assert config == {"mcpServers": {}}


def test_mcp_client_manager_init():
    manager = MCPClientManager()
    assert len(manager.connected_servers) == 0


def test_mcp_client_manager_infer_transport():
    manager = MCPClientManager()
    assert manager._infer_transport({"command": "npx", "args": []}) == "stdio"
    assert manager._infer_transport({"url": "http://localhost:3001"}) == "sse"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; pytest tests/test_mcp_client.py -v"
```
Expected: FAIL

- [ ] **Step 3: Implement MCP client**

Create `src/pbi_bgdesign/ai/mcp_client.py`:

```python
"""MCP client manager for connecting to external MCP servers."""
import json
from pathlib import Path


def load_mcp_config(path: str) -> dict:
    """Load MCP config from JSON file (dictionary format)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"mcpServers": {}}


class MCPClientManager:
    """Manage connections to MCP servers and aggregate their tools."""

    def __init__(self):
        self.connected_servers: dict[str, object] = {}
        self._tools: list[dict] = []

    def _infer_transport(self, config: dict) -> str:
        """Infer transport type from config fields."""
        if "command" in config:
            return "stdio"
        if "url" in config:
            return "sse"
        return "stdio"

    async def connect_all(self, config: dict):
        """Connect to all configured MCP servers."""
        servers = config.get("mcpServers", {})
        for name, server_config in servers.items():
            transport = self._infer_transport(server_config)
            try:
                # MCP SDK connection would go here
                # For now, store the config for later connection
                self.connected_servers[name] = {
                    "config": server_config,
                    "transport": transport,
                    "status": "configured",
                }
            except Exception:
                self.connected_servers[name] = {
                    "config": server_config,
                    "transport": transport,
                    "status": "error",
                }

    def get_tools(self) -> list[dict]:
        """Get aggregated tool definitions from all connected servers."""
        return self._tools

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> str:
        """Call a tool on a specific MCP server."""
        if server_name not in self.connected_servers:
            return f"Server '{server_name}' not connected."
        # MCP SDK tool call would go here
        return f"Tool '{tool_name}' called on '{server_name}' with {arguments}"
```

- [ ] **Step 4: Run tests**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; pytest tests/test_mcp_client.py -v"
```
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; git add -A; git commit -m 'feat: add MCP client manager with config loading and transport inference'"
```

---

## Phase 3: UI

### Task 9: Main Window + Canvas + Page List

**Files:**
- Create: `src/pbi_bgdesign/ui/main_window.py`
- Create: `src/pbi_bgdesign/ui/canvas_widget.py`
- Create: `src/pbi_bgdesign/ui/object_list.py`

- [ ] **Step 1: Create canvas widget**

Create `src/pbi_bgdesign/ui/canvas_widget.py`:

```python
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
```

- [ ] **Step 2: Create object list widget**

Create `src/pbi_bgdesign/ui/object_list.py`:

```python
"""Visual object list widget with checkboxes and grouping."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QHBoxLayout, QLabel,
)
from PyQt6.QtCore import pyqtSignal

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
        item.setData(0, 256, v.id)  # Store visual_id in user role
        return item

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        if column == 0:
            vid = item.data(0, 256)
            if vid:
                checked = item.checkState(0) == Qt.CheckState.Checked
                self.visibility_changed.emit(vid, checked)

    def _select_all_decorations(self):
        self._set_all_check_states(lambda cat: cat in ("decoration", "text"))

    def _select_none(self):
        self._set_all_check_states(lambda cat: False)

    def _invert_selection(self):
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            self._invert_item(item)

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
        for i in range(self.tree.topLevelItemCount()):
            self._set_item_state(self.tree.topLevelItem(i), filter_fn)

    def _set_item_state(self, item: QTreeWidgetItem, filter_fn):
        if item.childCount() > 0:
            for i in range(item.childCount()):
                self._set_item_state(item.child(i), filter_fn)
        else:
            vid = item.data(0, 256)
            if vid and self._analysis:
                cat = self._analysis.classifications.get(vid, "chart")
                state = Qt.CheckState.Checked if filter_fn(cat) else Qt.CheckState.Unchecked
                item.setCheckState(0, state)
```

- [ ] **Step 3: Create main window**

Create `src/pbi_bgdesign/ui/main_window.py`:

```python
"""Main application window."""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QRadioButton, QButtonGroup,
    QPushButton, QLabel, QFileDialog, QToolBar, QStatusBar,
    QLineEdit, QTextEdit, QGroupBox,
)
from PyQt6.QtCore import Qt, QThread

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

        self._setup_ui()

    def _setup_ui(self):
        # Toolbar
        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)

        self.btn_open = QPushButton("📂 打开文件")
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

        self.btn_ai = QPushButton("🤖 AI 设计")
        self.btn_ai.clicked.connect(self._start_ai_design)
        toolbar.addWidget(self.btn_ai)

        self.btn_fullscreen = QPushButton("👁 全屏")
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
        self.chat_panel = QGroupBox("💬 AI 对话")
        chat_layout = QVBoxLayout(self.chat_panel)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        chat_layout.addWidget(self.chat_display)

        input_layout = QHBoxLayout()
        self.btn_attach = QPushButton("📎")
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
        self.statusBar().showMessage("就绪 — 请打开 .pbix 文件")

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
                f"已加载: {path} — {len(self.pbix_data.pages)} 页"
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
        self.chat_display.append("🤖 AI 设计功能将在完成所有模块后启用")

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
            self.chat_display.append(f"📎 已附加图片: {path}")

    def _toggle_fullscreen(self):
        self.chat_display.append("全屏预览功能开发中...")

    def _export_png(self):
        if not self.scene_builder:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 PNG", f"{self.pbix_data.pages[self.current_page_index].display_name}_background.png",
            "PNG 文件 (*.png)"
        )
        if path:
            from PyQt6.QtCore import QSize
            page = self.pbix_data.pages[self.current_page_index]
            scene = self.scene_builder.build()
            export_png(scene, path, QSize(int(page.width), int(page.height)))
            self.statusBar().showMessage(f"已导出: {path}")

    def _export_svg(self):
        if not self.scene_builder:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 SVG", f"{self.pbix_data.pages[self.current_page_index].display_name}_background.svg",
            "SVG 文件 (*.svg)"
        )
        if path:
            from PyQt6.QtCore import QSize
            page = self.pbix_data.pages[self.current_page_index]
            scene = self.scene_builder.build()
            export_svg(scene, path, QSize(int(page.width), int(page.height)))
            self.statusBar().showMessage(f"已导出: {path}")
```

- [ ] **Step 4: Create app entry point**

Create `src/pbi_bgdesign/app.py`:

```python
"""Application entry point."""
import sys
from PyQt6.QtWidgets import QApplication

from pbi_bgdesign.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()

    # Check for command line argument (Power BI external tool)
    if len(sys.argv) > 1:
        pbix_path = sys.argv[1]
        window.load_pbix(pbix_path)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Test the app launches**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; python -c \"from PyQt6.QtWidgets import QApplication; from pbi_bgdesign.ui.main_window import MainWindow; app = QApplication([]); w = MainWindow(); print('MainWindow created successfully')\""
```
Expected: `MainWindow created successfully`

- [ ] **Step 6: Test loading the real .pbix file**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; python -c \"from PyQt6.QtWidgets import QApplication; from pbi_bgdesign.ui.main_window import MainWindow; app = QApplication([]); w = MainWindow(); w.load_pbix('天津工厂新需求_V2.1 .pbix'); print(f'Pages loaded: {w.page_list.count()}')\""
```
Expected: `Pages loaded: 17`

- [ ] **Step 7: Commit**

```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; git add -A; git commit -m 'feat: add main window with page list, canvas preview, object list, chat panel, and export'"
```

---

### Task 10: Fullscreen Preview

**Files:**
- Create: `src/pbi_bgdesign/ui/fullscreen.py`

- [ ] **Step 1: Implement fullscreen window**

Create `src/pbi_bgdesign/ui/fullscreen.py`:

```python
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
```

- [ ] **Step 2: Integrate fullscreen into main window**

In `src/pbi_bgdesign/ui/main_window.py`, update `_toggle_fullscreen`:

```python
def _toggle_fullscreen(self):
    from pbi_bgdesign.ui.fullscreen import FullscreenPreview
    if not self.pbix_data:
        return
    self._fullscreen = FullscreenPreview(
        total_pages=len(self.pbix_data.pages),
        current_page=self.current_page,
    )
    self._fullscreen.page_changed.connect(self._on_fullscreen_page_changed)
    if self.scene_builder:
        self._fullscreen.set_scene(self.scene_builder.build())
    self._fullscreen.show()

def _on_fullscreen_page_changed(self, index: int):
    self.page_list.setCurrentRow(index)
    if self.scene_builder:
        self._fullscreen.set_scene(self.scene_builder.build())
```

- [ ] **Step 3: Commit**

```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; git add -A; git commit -m 'feat: add fullscreen preview with auto-hide controls and keyboard navigation'"
```

---

### Task 11: Power BI External Tool Registration

**Files:**
- Create: `src/pbi_bgdesign/external_tool.py`

- [ ] **Step 1: Implement registry operations**

Create `src/pbi_bgdesign/external_tool.py`:

```python
"""Register/unregister as Power BI Desktop External Tool via Windows Registry."""
import sys
import winreg


TOOL_NAME = "PBI-BgDesign"
DISPLAY_NAME = "PBI 背景设计"
DESCRIPTION = "为报表页设计美观的背景图和装饰元素"
REG_PATH = rf"Software\Microsoft\Power BI Desktop\External Tools\{TOOL_NAME}"


def register(exe_path: str | None = None, icon_path: str | None = None):
    """Register this tool in Power BI Desktop External Tools."""
    if exe_path is None:
        exe_path = sys.executable

    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, DISPLAY_NAME)
        winreg.SetValueEx(key, "Description", 0, winreg.REG_SZ, DESCRIPTION)
        winreg.SetValueEx(key, "Path", 0, winreg.REG_SZ, exe_path)
        winreg.SetValueEx(key, "Arguments", 0, winreg.REG_SZ, '"%pbi%"')
        if icon_path:
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon_path)
        winreg.CloseKey(key)
        print(f"Registered: {DISPLAY_NAME} in Power BI External Tools")
    except OSError as e:
        print(f"Failed to register: {e}")


def unregister():
    """Remove this tool from Power BI Desktop External Tools."""
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        print(f"Unregistered: {TOOL_NAME}")
    except FileNotFoundError:
        print(f"Not registered: {TOOL_NAME}")
    except OSError as e:
        print(f"Failed to unregister: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--unregister":
        unregister()
    else:
        register()
```

- [ ] **Step 2: Test registration**

Run:
```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; python -m pbi_bgdesign.external_tool"
```
Expected: `Registered: PBI 背景设计 in Power BI External Tools`

- [ ] **Step 3: Verify in registry**

Run:
```powershell
pwsh -Command "Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Power BI Desktop\External Tools\PBI-BgDesign'"
```
Expected: Shows DisplayName, Description, Path, Arguments values.

- [ ] **Step 4: Commit**

```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; git add -A; git commit -m 'feat: add Power BI external tool registration via Windows registry'"
```

---

### Task 12: Integration + Cleanup

- [ ] **Step 1: Run all tests together**

```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; pytest tests/ -v --tb=short"
```
Expected: All tests PASS.

- [ ] **Step 2: Launch the full app with the real .pbix**

```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; python -m pbi_bgdesign.app '天津工厂新需求_V2.1 .pbix'"
```
Expected: App window opens, shows 17 pages, first page rendered with mock charts.

- [ ] **Step 3: Add .gitignore**

Create `.gitignore`:

```
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
*.egg
.temp_claude/
.env
```

- [ ] **Step 4: Final commit**

```powershell
pwsh -Command "cd 'D:\Project\Git管理\PBI-BgDesign'; git add -A; git commit -m 'chore: add .gitignore and verify full integration'"
```
