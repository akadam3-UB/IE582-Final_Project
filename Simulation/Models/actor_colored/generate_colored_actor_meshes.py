#!/usr/bin/env python3
"""Create shirt-color variants of the cached Gazebo actor DAE files."""

from __future__ import annotations

import os
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent
MESH_DIR = ROOT / "meshes"
CACHE = Path.home() / ".gz" / "fuel" / "fuel.gazebosim.org" / "mingfei" / "models" / "actor" / "1" / "meshes"

SOURCE_FILES = {
    "talk_b": CACHE / "talk_b.dae",
    "walk": CACHE / "walk.dae",
}

COLORS = {
    "red": "0.86 0.04 0.03 1",
    "green": "0.04 0.55 0.18 1",
    "blue": "0.04 0.16 0.86 1",
    "yellow": "0.95 0.76 0.04 1",
}

NS = {"c": "http://www.collada.org/2005/11/COLLADASchema"}
ET.register_namespace("", NS["c"])


def recolor_sweater(source: Path, destination: Path, color: str) -> None:
    tree = ET.parse(source)
    root = tree.getroot()
    changed = 0

    for effect in root.findall(".//c:effect", NS):
        effect_id = effect.attrib.get("id", "")
        if not effect_id.startswith("sweater-"):
            continue
        for color_node in effect.findall(".//c:color", NS):
            sid = color_node.attrib.get("sid")
            if sid in {"ambient", "diffuse"}:
                color_node.text = color
                changed += 1

    if changed == 0:
        raise RuntimeError(f"No sweater color entries found in {source}")

    ET.indent(tree, space="  ")
    destination.parent.mkdir(parents=True, exist_ok=True)
    tree.write(destination, encoding="utf-8", xml_declaration=True)


def main() -> None:
    missing = [str(path) for path in SOURCE_FILES.values() if not path.exists()]
    if missing:
        raise SystemExit("Cached actor mesh not found. Open the actor once in Gazebo so Fuel downloads it:\n" + "\n".join(missing))

    for animation, source in SOURCE_FILES.items():
        for color_name, color_value in COLORS.items():
            recolor_sweater(source, MESH_DIR / f"{animation}_{color_name}.dae", color_value)


if __name__ == "__main__":
    main()
