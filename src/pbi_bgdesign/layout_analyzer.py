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
