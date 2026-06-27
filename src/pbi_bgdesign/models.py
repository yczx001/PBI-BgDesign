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
