#!/usr/bin/env python3
"""Generate the detailed Room 427 furniture and local person proxy models."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, sin
from pathlib import Path
from typing import Iterable, Tuple


ROOT = Path(__file__).resolve().parent
MODELS_DIR = ROOT / "Models"
SDF_VERSION = "1.10"


@dataclass(frozen=True)
class Material:
    ambient: str
    diffuse: str
    specular: str = "0.18 0.18 0.18 1"
    emissive: str | None = None
    transparency: float | None = None


MATERIALS = {
    "black_tile": Material("0.01 0.01 0.01 1", "0.055 0.055 0.052 1", "0.5 0.5 0.48 1"),
    "tile_grout": Material("0.13 0.13 0.13 1", "0.16 0.16 0.15 1", "0.04 0.04 0.04 1"),
    "yellow_tape": Material("1.0 0.82 0.02 1", "1.0 0.82 0.02 1", "0.25 0.22 0.04 1"),
    "table_top": Material("0.58 0.46 0.32 1", "0.62 0.49 0.34 1", "0.22 0.18 0.12 1"),
    "table_edge": Material("0.18 0.18 0.19 1", "0.22 0.22 0.23 1", "0.35 0.35 0.35 1"),
    "metal": Material("0.36 0.36 0.37 1", "0.42 0.42 0.43 1", "0.45 0.45 0.45 1"),
    "rubber": Material("0.035 0.035 0.035 1", "0.045 0.045 0.045 1", "0.08 0.08 0.08 1"),
    "chair_seat": Material("0.10 0.17 0.28 1", "0.12 0.22 0.38 1", "0.18 0.2 0.24 1"),
    "chair_frame": Material("0.20 0.20 0.21 1", "0.27 0.27 0.28 1", "0.35 0.35 0.35 1"),
    "cabinet_blue": Material("0.00 0.16 0.35 1", "0.00 0.20 0.45 1", "0.28 0.32 0.38 1"),
    "cabinet_handle": Material("0.78 0.78 0.72 1", "0.86 0.86 0.80 1", "0.45 0.45 0.40 1"),
    "rack": Material("0.18 0.18 0.18 1", "0.26 0.26 0.25 1", "0.25 0.25 0.25 1"),
    "box_cardboard": Material("0.55 0.38 0.20 1", "0.68 0.48 0.26 1", "0.08 0.06 0.04 1"),
    "tote_orange": Material("0.88 0.34 0.05 1", "0.96 0.42 0.08 1", "0.20 0.14 0.06 1"),
    "tote_gray": Material("0.32 0.34 0.34 1", "0.43 0.45 0.45 1", "0.16 0.16 0.16 1"),
    "whiteboard": Material("0.96 0.96 0.92 1", "0.98 0.98 0.94 1", "0.25 0.25 0.25 1"),
    "marker_black": Material("0.0 0.0 0.0 1", "0.0 0.0 0.0 1", "0.05 0.05 0.05 1"),
    "marker_white": Material("1 1 1 1", "1 1 1 1", "0.08 0.08 0.08 1"),
    "blind": Material("0.72 0.72 0.68 1", "0.78 0.78 0.74 1", "0.12 0.12 0.12 1"),
    "skin": Material("0.72 0.48 0.34 1", "0.76 0.52 0.38 1", "0.12 0.08 0.06 1"),
    "hair": Material("0.06 0.045 0.035 1", "0.08 0.06 0.045 1", "0.04 0.03 0.02 1"),
    "pants": Material("0.06 0.08 0.13 1", "0.08 0.11 0.18 1", "0.10 0.10 0.12 1"),
    "shoe": Material("0.02 0.02 0.02 1", "0.03 0.03 0.03 1", "0.05 0.05 0.05 1"),
}


PERSON_SHIRTS = {
    "red": Material("0.72 0.08 0.07 1", "0.86 0.10 0.09 1", "0.18 0.05 0.05 1"),
    "green": Material("0.08 0.42 0.16 1", "0.10 0.58 0.22 1", "0.06 0.16 0.08 1"),
    "blue": Material("0.06 0.18 0.64 1", "0.08 0.24 0.82 1", "0.05 0.08 0.18 1"),
    "yellow": Material("0.78 0.58 0.04 1", "0.95 0.72 0.08 1", "0.18 0.14 0.04 1"),
}


def fmt(value: float) -> str:
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return text if text else "0"


def pose(values: Iterable[float]) -> str:
    return " ".join(fmt(float(v)) for v in values)


def material_xml(material: Material, indent: str = "        ") -> str:
    lines = [
        f"{indent}<material>",
        f"{indent}  <ambient>{material.ambient}</ambient>",
        f"{indent}  <diffuse>{material.diffuse}</diffuse>",
        f"{indent}  <specular>{material.specular}</specular>",
    ]
    if material.emissive is not None:
        lines.append(f"{indent}  <emissive>{material.emissive}</emissive>")
    lines.append(f"{indent}</material>")
    if material.transparency is not None:
        lines.append(f"{indent}<transparency>{fmt(material.transparency)}</transparency>")
    return "\n".join(lines)


def rotate_xy(x: float, y: float, yaw: float) -> Tuple[float, float]:
    return (x * cos(yaw) - y * sin(yaw), x * sin(yaw) + y * cos(yaw))


def world_pose(
    base_x: float,
    base_y: float,
    base_z: float,
    base_yaw: float,
    local_x: float,
    local_y: float,
    local_z: float,
    local_yaw: float = 0.0,
    roll: float = 0.0,
    pitch: float = 0.0,
) -> Tuple[float, float, float, float, float, float]:
    dx, dy = rotate_xy(local_x, local_y, base_yaw)
    return (base_x + dx, base_y + dy, base_z + local_z, roll, pitch, base_yaw + local_yaw)


def box_link(
    name: str,
    box_pose: Tuple[float, float, float, float, float, float],
    size: Tuple[float, float, float],
    material: Material,
    collision: bool = True,
) -> str:
    collision_xml = ""
    if collision:
        collision_xml = f"""
      <collision name="collision">
        <geometry><box><size>{pose(size)}</size></box></geometry>
      </collision>"""
    return f"""
    <link name="{name}">
      <pose>{pose(box_pose)}</pose>{collision_xml}
      <visual name="visual">
        <geometry><box><size>{pose(size)}</size></box></geometry>
{material_xml(material)}
      </visual>
    </link>"""


def cylinder_link(
    name: str,
    cyl_pose: Tuple[float, float, float, float, float, float],
    radius: float,
    length: float,
    material: Material,
    collision: bool = True,
) -> str:
    collision_xml = ""
    if collision:
        collision_xml = f"""
      <collision name="collision">
        <geometry><cylinder><radius>{fmt(radius)}</radius><length>{fmt(length)}</length></cylinder></geometry>
      </collision>"""
    return f"""
    <link name="{name}">
      <pose>{pose(cyl_pose)}</pose>{collision_xml}
      <visual name="visual">
        <geometry><cylinder><radius>{fmt(radius)}</radius><length>{fmt(length)}</length></cylinder></geometry>
{material_xml(material)}
      </visual>
    </link>"""


def sphere_link(
    name: str,
    sphere_pose: Tuple[float, float, float, float, float, float],
    radius: float,
    material: Material,
    collision: bool = True,
) -> str:
    collision_xml = ""
    if collision:
        collision_xml = f"""
      <collision name="collision">
        <geometry><sphere><radius>{fmt(radius)}</radius></sphere></geometry>
      </collision>"""
    return f"""
    <link name="{name}">
      <pose>{pose(sphere_pose)}</pose>{collision_xml}
      <visual name="visual">
        <geometry><sphere><radius>{fmt(radius)}</radius></sphere></geometry>
{material_xml(material)}
      </visual>
    </link>"""


def add_mobile_table(parts: list[str], prefix: str, x: float, y: float, yaw: float = 0.0) -> None:
    parts.append(
        box_link(
            f"{prefix}_top",
            world_pose(x, y, 0, yaw, 0, 0, 0.82),
            (1.22, 0.61, 0.055),
            MATERIALS["table_top"],
        )
    )
    parts.append(
        box_link(
            f"{prefix}_front_edge",
            world_pose(x, y, 0, yaw, 0.0, 0.332, 0.79),
            (1.26, 0.035, 0.09),
            MATERIALS["table_edge"],
        )
    )
    parts.append(
        box_link(
            f"{prefix}_back_edge",
            world_pose(x, y, 0, yaw, 0.0, -0.332, 0.79),
            (1.26, 0.035, 0.09),
            MATERIALS["table_edge"],
        )
    )
    for idx, (lx, ly) in enumerate(((0.53, 0.23), (0.53, -0.23), (-0.53, 0.23), (-0.53, -0.23)), start=1):
        parts.append(
            box_link(
                f"{prefix}_leg_{idx}",
                world_pose(x, y, 0, yaw, lx, ly, 0.42),
                (0.055, 0.055, 0.74),
                MATERIALS["metal"],
            )
        )
        parts.append(
            cylinder_link(
                f"{prefix}_caster_{idx}",
                world_pose(x, y, 0, yaw, lx, ly, 0.07, roll=1.5708),
                0.055,
                0.045,
                MATERIALS["rubber"],
            )
        )


def add_chair(parts: list[str], prefix: str, x: float, y: float, yaw: float = 0.0) -> None:
    parts.append(
        box_link(
            f"{prefix}_seat",
            world_pose(x, y, 0, yaw, 0, 0, 0.46),
            (0.50, 0.48, 0.075),
            MATERIALS["chair_seat"],
        )
    )
    parts.append(
        box_link(
            f"{prefix}_back",
            world_pose(x, y, 0, yaw, -0.23, 0, 0.79),
            (0.08, 0.52, 0.64),
            MATERIALS["chair_seat"],
        )
    )
    for idx, (lx, ly) in enumerate(((0.18, 0.18), (0.18, -0.18), (-0.18, 0.18), (-0.18, -0.18)), start=1):
        parts.append(
            cylinder_link(
                f"{prefix}_leg_{idx}",
                world_pose(x, y, 0, yaw, lx, ly, 0.23),
                0.022,
                0.43,
                MATERIALS["chair_frame"],
            )
        )


def add_cabinet(parts: list[str], prefix: str, x: float, y: float, yaw: float, width: float = 1.15) -> None:
    parts.append(box_link(f"{prefix}_body", world_pose(x, y, 0, yaw, 0, 0, 0.88), (width, 0.42, 1.76), MATERIALS["cabinet_blue"]))
    parts.append(box_link(f"{prefix}_top_trim", world_pose(x, y, 0, yaw, 0, 0, 1.78), (width + 0.05, 0.45, 0.05), MATERIALS["metal"]))
    parts.append(box_link(f"{prefix}_left_handle", world_pose(x, y, 0, yaw, -0.18, -0.215, 1.02), (0.035, 0.03, 0.45), MATERIALS["cabinet_handle"], collision=False))
    parts.append(box_link(f"{prefix}_right_handle", world_pose(x, y, 0, yaw, 0.18, -0.215, 1.02), (0.035, 0.03, 0.45), MATERIALS["cabinet_handle"], collision=False))


def add_rack(parts: list[str], prefix: str, x: float, y: float, yaw: float) -> None:
    for shelf_idx, z in enumerate((0.35, 0.88, 1.41), start=1):
        parts.append(box_link(f"{prefix}_shelf_{shelf_idx}", world_pose(x, y, 0, yaw, 0, 0, z), (1.50, 0.44, 0.045), MATERIALS["rack"]))
    for idx, (lx, ly) in enumerate(((0.70, 0.19), (0.70, -0.19), (-0.70, 0.19), (-0.70, -0.19)), start=1):
        parts.append(box_link(f"{prefix}_post_{idx}", world_pose(x, y, 0, yaw, lx, ly, 0.86), (0.045, 0.045, 1.45), MATERIALS["metal"]))


def add_workcell(parts: list[str], prefix: str, x: float, y: float, yaw: float) -> None:
    add_mobile_table(parts, f"{prefix}_bench", x, y, yaw)
    parts.append(box_link(f"{prefix}_guard_left", world_pose(x, y, 0, yaw, -0.66, 0, 1.15), (0.035, 0.80, 0.62), MATERIALS["rack"], collision=False))
    parts.append(box_link(f"{prefix}_guard_back", world_pose(x, y, 0, yaw, 0, 0.41, 1.15), (1.36, 0.035, 0.62), MATERIALS["rack"], collision=False))
    parts.append(box_link(f"{prefix}_fixture_base", world_pose(x, y, 0, yaw, 0.18, 0, 0.90), (0.36, 0.24, 0.08), MATERIALS["metal"]))
    parts.append(cylinder_link(f"{prefix}_tool_column", world_pose(x, y, 0, yaw, 0.18, 0, 1.12), 0.045, 0.42, MATERIALS["metal"]))
    parts.append(box_link(f"{prefix}_tool_head", world_pose(x, y, 0, yaw, 0.30, 0, 1.32), (0.26, 0.16, 0.12), MATERIALS["cabinet_blue"]))


def add_boxes(parts: list[str], prefix: str, placements: Iterable[Tuple[float, float, float, float, str]]) -> None:
    for idx, (x, y, z, yaw, material_name) in enumerate(placements, start=1):
        parts.append(
            box_link(
                f"{prefix}_{idx}",
                (x, y, z, 0, 0, yaw),
                (0.42, 0.32, 0.24),
                MATERIALS[material_name],
            )
        )


def add_yellow_tape(parts: list[str]) -> None:
    # Segment coordinates are room-local in the existing 24.2 m x 6.54 m Room 427 frame.
    segments = [
        ("front_run", 12.1, 0.78, 15.8, 0.06, 0.0),
        ("front_left_turn", 4.2, 1.33, 1.10, 0.06, 1.5708),
        ("front_right_turn", 20.0, 1.35, 1.14, 0.06, 1.5708),
        ("center_run_left", 6.7, 2.44, 5.0, 0.06, 0.0),
        ("center_run_right", 14.6, 2.44, 7.1, 0.06, 0.0),
        ("middle_step_left", 9.3, 2.80, 0.82, 0.06, 0.72),
        ("middle_step_right", 11.0, 2.80, 0.82, 0.06, -0.72),
        ("back_run", 12.2, 5.55, 14.7, 0.06, 0.0),
        ("back_left_drop", 5.0, 4.86, 1.38, 0.06, 1.5708),
        ("back_right_drop", 19.4, 4.86, 1.38, 0.06, 1.5708),
        ("workcell_box_front", 17.95, 3.78, 2.30, 0.06, 0.0),
        ("workcell_box_back", 17.95, 5.02, 2.30, 0.06, 0.0),
        ("workcell_box_left", 16.80, 4.40, 1.24, 0.06, 1.5708),
        ("workcell_box_right", 19.10, 4.40, 1.24, 0.06, 1.5708),
        ("door_jog", 22.0, 5.85, 1.55, 0.06, 0.0),
        ("door_short_drop", 22.75, 5.35, 1.0, 0.06, 1.5708),
    ]
    for name, x, y, length, width, yaw in segments:
        parts.append(box_link(f"yellow_tape_{name}", (x, y, 0.036, 0, 0, yaw), (length, width, 0.006), MATERIALS["yellow_tape"], collision=False))


def add_tile_seams(parts: list[str]) -> None:
    for idx in range(1, 49):
        x = idx * 0.5
        if x >= 24.2:
            continue
        parts.append(box_link(f"tile_seam_x_{idx}", (x, 3.27, 0.032, 0, 0, 0), (0.012, 6.54, 0.004), MATERIALS["tile_grout"], collision=False))
    for idx in range(1, 14):
        y = idx * 0.5
        if y >= 6.54:
            continue
        parts.append(box_link(f"tile_seam_y_{idx}", (12.1, y, 0.033, 0, 0, 0), (24.2, 0.012, 0.004), MATERIALS["tile_grout"], collision=False))


def add_blinds(parts: list[str]) -> None:
    window_centers = [1.45, 4.49, 7.53, 10.57, 13.61, 16.65, 19.69, 22.73]
    for w_idx, x in enumerate(window_centers, start=1):
        for s_idx, z in enumerate((2.25, 2.08, 1.91, 1.74, 1.57, 1.40), start=1):
            parts.append(box_link(f"blind_{w_idx}_{s_idx}", (x, 0.085, z, 0, 0, 0), (2.06, 0.024, 0.035), MATERIALS["blind"], collision=False))
        parts.append(box_link(f"blind_{w_idx}_pull", (x + 0.98, 0.105, 1.62, 0, 0, 0), (0.018, 0.018, 0.96), MATERIALS["cabinet_handle"], collision=False))


def add_apriltag_board(parts: list[str]) -> None:
    x, y, z = 3.0, 6.335, 1.55
    parts.append(box_link("aruco_board", (x, y, z, 0, 0, 0), (1.20, 0.035, 0.70), MATERIALS["whiteboard"]))
    tag_x, tag_y, tag_z = x - 0.36, y - 0.025, z
    parts.append(box_link("aruco_tag_outer", (tag_x, tag_y, tag_z, 0, 0, 0), (0.32, 0.012, 0.32), MATERIALS["marker_black"], collision=False))
    parts.append(box_link("aruco_tag_inner", (tag_x, tag_y - 0.002, tag_z, 0, 0, 0), (0.23, 0.012, 0.23), MATERIALS["marker_white"], collision=False))
    for idx, (dx, dz, sx, sz) in enumerate(
        (
            (-0.055, 0.055, 0.065, 0.065),
            (0.055, 0.055, 0.065, 0.065),
            (-0.055, -0.055, 0.065, 0.065),
            (0.055, -0.055, 0.045, 0.045),
            (0.0, 0.0, 0.045, 0.045),
        ),
        start=1,
    ):
        parts.append(box_link(f"aruco_tag_cell_{idx}", (tag_x + dx, tag_y - 0.004, tag_z + dz, 0, 0, 0), (sx, 0.014, sz), MATERIALS["marker_black"], collision=False))


def build_furnishings_model() -> str:
    parts: list[str] = []
    add_tile_seams(parts)
    add_yellow_tape(parts)
    add_blinds(parts)
    add_apriltag_board(parts)

    table_positions = [
        (4.6, 1.34), (7.9, 1.34), (11.2, 1.34), (14.5, 1.34),
        (4.6, 4.32), (7.9, 4.32), (11.2, 4.32), (14.5, 4.32),
    ]
    for idx, (x, y) in enumerate(table_positions, start=1):
        add_mobile_table(parts, f"student_table_{idx}", x, y, 0.0)
        add_chair(parts, f"student_chair_{idx}_south", x - 0.36, y - 0.78, 1.5708)
        add_chair(parts, f"student_chair_{idx}_north", x + 0.36, y + 0.78, -1.5708)

    add_mobile_table(parts, "instructor_demo_table", 20.95, 2.10, 0.0)
    add_chair(parts, "instructor_chair", 21.85, 2.10, 3.1416)
    add_rack(parts, "mini_factory_rack", 20.45, 4.78, 0.0)
    add_workcell(parts, "robot_workcell", 16.35, 4.68, 0.0)

    add_cabinet(parts, "blue_cabinet_left", 9.45, 5.92, 0.0)
    add_cabinet(parts, "blue_cabinet_mid", 11.25, 5.92, 0.0)
    add_cabinet(parts, "blue_cabinet_right", 13.05, 5.92, 0.0)
    add_cabinet(parts, "blue_cabinet_far_right", 22.65, 5.80, 0.0, width=1.05)

    add_boxes(
        parts,
        "loose_box",
        (
            (18.45, 4.95, 0.22, 0.08, "box_cardboard"),
            (19.08, 5.20, 0.22, -0.12, "tote_orange"),
            (20.45, 4.75, 1.02, 0.0, "tote_gray"),
            (20.10, 4.75, 1.55, 0.0, "box_cardboard"),
            (21.0, 4.75, 0.48, 0.0, "tote_orange"),
            (16.10, 5.28, 0.95, 0.05, "tote_gray"),
        ),
    )

    return f"""<?xml version="1.0" ?>
<sdf version="{SDF_VERSION}">
  <model name="room_427_furnishings">
    <static>true</static>
{''.join(parts)}
  </model>
</sdf>
"""


def build_person_proxy_model(color_name: str) -> str:
    shirt = PERSON_SHIRTS[color_name]
    parts = [
        cylinder_link("torso", (0, 0, 1.04, 0, 0, 0), 0.18, 0.74, shirt),
        sphere_link("head", (0, 0, 1.55, 0, 0, 0), 0.15, MATERIALS["skin"]),
        sphere_link("hair", (0, 0, 1.67, 0, 0, 0), 0.155, MATERIALS["hair"], collision=False),
        cylinder_link("left_arm", (0, 0.22, 1.08, 0.18, 0, 0), 0.045, 0.62, MATERIALS["skin"]),
        cylinder_link("right_arm", (0, -0.22, 1.08, -0.18, 0, 0), 0.045, 0.62, MATERIALS["skin"]),
        cylinder_link("left_leg", (0, 0.08, 0.46, 0, 0, 0), 0.06, 0.82, MATERIALS["pants"]),
        cylinder_link("right_leg", (0, -0.08, 0.46, 0, 0, 0), 0.06, 0.82, MATERIALS["pants"]),
        box_link("left_shoe", (0.03, 0.08, 0.045, 0, 0, 0), (0.20, 0.09, 0.06), MATERIALS["shoe"]),
        box_link("right_shoe", (0.03, -0.08, 0.045, 0, 0, 0), (0.20, 0.09, 0.06), MATERIALS["shoe"]),
    ]
    return f"""<?xml version="1.0" ?>
<sdf version="{SDF_VERSION}">
  <model name="person_proxy_{color_name}">
    <static>true</static>
{''.join(parts)}
  </model>
</sdf>
"""


def model_config(name: str, description: str) -> str:
    return f"""<?xml version="1.0" ?>
<model>
  <name>{name}</name>
  <version>1.0</version>
  <sdf version="{SDF_VERSION}">model.sdf</sdf>
  <author>
    <name>Abhijeet Kadam</name>
  </author>
  <description>{description}</description>
</model>
"""


def write_model(name: str, sdf_text: str, description: str) -> None:
    out_dir = MODELS_DIR / name
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "model.sdf").write_text(sdf_text, encoding="utf-8")
    (out_dir / "model.config").write_text(model_config(name, description), encoding="utf-8")


def main() -> None:
    write_model(
        "room_427_furnishings",
        build_furnishings_model(),
        "Detailed Room 427 furniture, floor tape, tile seams, cabinets, lab props, blinds, and AprilTag board.",
    )
    for color_name in PERSON_SHIRTS:
        write_model(
            f"person_proxy_{color_name}",
            build_person_proxy_model(color_name),
            f"Local stylized standing person proxy with a {color_name} shirt for Gazebo tracking demos.",
        )


if __name__ == "__main__":
    main()
