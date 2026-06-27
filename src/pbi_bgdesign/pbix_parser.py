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
