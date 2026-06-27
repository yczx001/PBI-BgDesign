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
