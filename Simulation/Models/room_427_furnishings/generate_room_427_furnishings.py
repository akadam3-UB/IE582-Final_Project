#!/usr/bin/env python3
"""Generate the detailed Room 427 furniture and local person proxy models."""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, sin, sqrt
from pathlib import Path
from typing import Iterable, Tuple


ROOT = Path(__file__).resolve().parent
MODELS_DIR = ROOT.parent
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
    "screen_border": Material("0.04 0.04 0.045 1", "0.05 0.05 0.055 1", "0.12 0.12 0.12 1"),
    "screen_surface": Material("0.88 0.90 0.88 1", "0.96 0.98 0.96 1", "0.18 0.18 0.18 1"),
    "podium_wood": Material("0.36 0.22 0.12 1", "0.45 0.29 0.16 1", "0.18 0.12 0.08 1"),
    "projector": Material("0.78 0.78 0.76 1", "0.86 0.86 0.83 1", "0.35 0.35 0.34 1"),
    "door_wood": Material("0.42 0.25 0.13 1", "0.52 0.31 0.16 1", "0.16 0.10 0.06 1"),
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


def cylinder_between(
    name: str,
    start: Tuple[float, float, float],
    end: Tuple[float, float, float],
    radius: float,
    material: Material,
    collision: bool = True,
) -> str:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dz = end[2] - start[2]
    length = sqrt(dx * dx + dy * dy + dz * dz)
    horizontal = sqrt(dx * dx + dy * dy)
    yaw = atan2(dy, dx) if horizontal > 1e-6 else 0.0
    pitch = atan2(horizontal, dz)
    center = (
        (start[0] + end[0]) * 0.5,
        (start[1] + end[1]) * 0.5,
        (start[2] + end[2]) * 0.5,
        0.0,
        pitch,
        yaw,
    )
    return cylinder_link(name, center, radius, length, material, collision)


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


def add_plastic_wheel_chair(parts: list[str], prefix: str, x: float, y: float, yaw: float = 0.0) -> None:
    parts.append(box_link(f"{prefix}_seat", world_pose(x, y, 0, yaw, 0, 0, 0.48), (0.48, 0.47, 0.075), MATERIALS["chair_seat"]))
    parts.append(box_link(f"{prefix}_back", world_pose(x, y, 0, yaw, -0.22, 0, 0.82), (0.07, 0.50, 0.62), MATERIALS["chair_seat"]))
    parts.append(cylinder_link(f"{prefix}_gas_lift", world_pose(x, y, 0, yaw, 0, 0, 0.30), 0.038, 0.46, MATERIALS["chair_frame"]))
    for idx, angle in enumerate((0.0, 1.2566, 2.5133, 3.7699, 5.0265), start=1):
        lx, ly = rotate_xy(0.26, 0, angle)
        parts.append(box_link(f"{prefix}_star_arm_{idx}", world_pose(x, y, 0, yaw, lx * 0.5, ly * 0.5, 0.10, angle), (0.30, 0.035, 0.035), MATERIALS["chair_frame"]))
        parts.append(cylinder_link(f"{prefix}_caster_{idx}", world_pose(x, y, 0, yaw, lx, ly, 0.065, angle, roll=1.5708), 0.045, 0.035, MATERIALS["rubber"]))


def add_high_chair(parts: list[str], prefix: str, x: float, y: float, yaw: float = 0.0) -> None:
    parts.append(box_link(f"{prefix}_seat", world_pose(x, y, 0, yaw, 0, 0, 0.76), (0.42, 0.42, 0.065), MATERIALS["chair_seat"]))
    parts.append(box_link(f"{prefix}_back", world_pose(x, y, 0, yaw, -0.20, 0, 1.10), (0.06, 0.44, 0.55), MATERIALS["chair_seat"]))
    for idx, (lx, ly) in enumerate(((0.15, 0.15), (0.15, -0.15), (-0.15, 0.15), (-0.15, -0.15)), start=1):
        parts.append(cylinder_link(f"{prefix}_leg_{idx}", world_pose(x, y, 0, yaw, lx, ly, 0.39), 0.022, 0.74, MATERIALS["chair_frame"]))
    parts.append(cylinder_link(f"{prefix}_foot_ring_front", world_pose(x, y, 0, yaw, 0.0, 0.22, 0.37, roll=1.5708), 0.018, 0.46, MATERIALS["chair_frame"], collision=False))
    parts.append(cylinder_link(f"{prefix}_foot_ring_back", world_pose(x, y, 0, yaw, 0.0, -0.22, 0.37, roll=1.5708), 0.018, 0.46, MATERIALS["chair_frame"], collision=False))


def add_fixed_bench(parts: list[str], prefix: str, x: float, y: float, yaw: float = 1.5708) -> None:
    parts.append(box_link(f"{prefix}_top", world_pose(x, y, 0, yaw, 0, 0, 0.73), (1.65, 0.48, 0.055), MATERIALS["table_top"]))
    parts.append(box_link(f"{prefix}_front_apron", world_pose(x, y, 0, yaw, 0, 0.265, 0.66), (1.69, 0.035, 0.14), MATERIALS["table_edge"]))
    parts.append(box_link(f"{prefix}_back_apron", world_pose(x, y, 0, yaw, 0, -0.265, 0.66), (1.69, 0.035, 0.14), MATERIALS["table_edge"]))
    for idx, (lx, ly) in enumerate(((0.72, 0.19), (0.72, -0.19), (-0.72, 0.19), (-0.72, -0.19)), start=1):
        parts.append(box_link(f"{prefix}_leg_{idx}", world_pose(x, y, 0, yaw, lx, ly, 0.36), (0.06, 0.06, 0.68), MATERIALS["metal"]))


def add_projection_area(parts: list[str]) -> None:
    parts.append(box_link("projector_screen_surface", (0.085, 3.20, 1.58, 0, 0, 0), (0.035, 2.70, 1.28), MATERIALS["screen_surface"], collision=False))
    parts.append(box_link("projector_screen_top_rail", (0.10, 3.20, 2.24, 0, 0, 0), (0.055, 2.86, 0.055), MATERIALS["screen_border"], collision=False))
    parts.append(box_link("projector_screen_bottom_rail", (0.10, 3.20, 0.92, 0, 0, 0), (0.055, 2.86, 0.045), MATERIALS["screen_border"], collision=False))
    parts.append(box_link("projector_screen_left_rail", (0.10, 1.77, 1.58, 0, 0, 0), (0.055, 0.045, 1.36), MATERIALS["screen_border"], collision=False))
    parts.append(box_link("projector_screen_right_rail", (0.10, 4.63, 1.58, 0, 0, 0), (0.055, 0.045, 1.36), MATERIALS["screen_border"], collision=False))

    parts.append(box_link("professor_podium_body", (0.95, 4.70, 0.55, 0, 0, 0), (0.70, 0.52, 1.10), MATERIALS["podium_wood"]))
    parts.append(box_link("professor_podium_sloped_top", (0.88, 4.70, 1.13, 0, 0.12, 0), (0.76, 0.56, 0.075), MATERIALS["podium_wood"]))
    parts.append(box_link("professor_podium_panel", (0.58, 4.70, 0.82, 0, 0, 0), (0.055, 0.50, 0.46), MATERIALS["table_edge"], collision=False))
    parts.append(cylinder_link("podium_microphone_stem", (0.62, 4.58, 1.30, 0.28, 0, 0), 0.012, 0.28, MATERIALS["marker_black"], collision=False))
    parts.append(sphere_link("podium_microphone_head", (0.57, 4.52, 1.42, 0, 0, 0), 0.035, MATERIALS["marker_black"], collision=False))

    parts.append(box_link("ceiling_projector_body", (3.20, 3.22, 2.43, 0, 0, 0), (0.48, 0.32, 0.16), MATERIALS["projector"], collision=False))
    parts.append(cylinder_link("ceiling_projector_lens", (2.92, 3.22, 2.43, 0, 1.5708, 0), 0.065, 0.12, MATERIALS["screen_border"], collision=False))
    parts.append(box_link("ceiling_projector_mount", (3.20, 3.22, 2.58, 0, 0, 0), (0.08, 0.08, 0.28), MATERIALS["metal"], collision=False))


def add_front_wall_door(parts: list[str]) -> None:
    parts.append(box_link("front_wall_demo_door_panel", (0.075, 5.42, 1.05, 0, 0, 0), (0.045, 0.92, 2.10), MATERIALS["door_wood"], collision=False))
    parts.append(cylinder_link("front_wall_demo_door_handle", (0.035, 5.03, 1.08, 0, 1.5708, 0), 0.035, 0.04, MATERIALS["cabinet_handle"], collision=False))


def add_conveyor(parts: list[str], prefix: str, x: float, y: float, yaw: float, length: float = 3.6) -> None:
    parts.append(box_link(f"{prefix}_frame", world_pose(x, y, 0, yaw, 0, 0, 0.42), (length, 0.56, 0.16), MATERIALS["metal"]))
    parts.append(box_link(f"{prefix}_belt", world_pose(x, y, 0, yaw, 0, 0, 0.53), (length - 0.16, 0.44, 0.035), MATERIALS["rubber"]))
    for idx, lx in enumerate((-length / 2 + 0.38, length / 2 - 0.38), start=1):
        parts.append(cylinder_link(f"{prefix}_roller_{idx}", world_pose(x, y, 0, yaw, lx, 0, 0.55, roll=1.5708), 0.09, 0.50, MATERIALS["rack"]))
    for idx, (lx, ly) in enumerate(((length / 2 - 0.32, 0.22), (length / 2 - 0.32, -0.22), (-length / 2 + 0.32, 0.22), (-length / 2 + 0.32, -0.22)), start=1):
        parts.append(box_link(f"{prefix}_leg_{idx}", world_pose(x, y, 0, yaw, lx, ly, 0.24), (0.055, 0.055, 0.44), MATERIALS["metal"]))


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
    # The tape marks the student aisle, the teaching clearance, the door approaches, and the conveyor boundary.
    segments = [
        ("front_teaching_clearance", 2.25, 3.27, 5.70, 0.06, 1.5708),
        ("student_aisle_window_edge", 7.95, 2.90, 11.40, 0.06, 0.0),
        ("student_aisle_door_edge", 7.95, 3.64, 11.40, 0.06, 0.0),
        ("class_conveyor_divider", 13.90, 3.27, 5.70, 0.06, 1.5708),
        ("front_door_approach", 1.10, 5.42, 2.10, 0.06, 0.0),
        ("front_door_side_mark_a", 0.72, 4.96, 0.82, 0.06, 1.5708),
        ("front_door_side_mark_b", 0.72, 5.88, 0.82, 0.06, 1.5708),
        ("back_door_run", 17.85, 5.78, 8.45, 0.06, 0.0),
        ("back_door_2_left_side", 13.08, 6.02, 0.48, 0.06, 1.5708),
        ("back_door_2_right_side", 14.92, 6.02, 0.48, 0.06, 1.5708),
        ("back_door_1_left_side", 20.84, 6.02, 0.48, 0.06, 1.5708),
        ("back_door_1_right_side", 22.56, 6.02, 0.48, 0.06, 1.5708),
        ("conveyor_front_boundary", 18.50, 2.58, 6.40, 0.06, 0.0),
        ("conveyor_back_boundary", 18.50, 4.92, 6.40, 0.06, 0.0),
        ("conveyor_exit_to_back_door", 21.70, 5.35, 0.86, 0.06, 1.5708),
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

    add_projection_area(parts)
    add_front_wall_door(parts)

    fixed_benches = [
        ("front_right", 3.45, 1.70),
        ("front_left", 3.45, 4.66),
        ("rear_right", 5.45, 1.70),
        ("rear_left", 5.45, 4.66),
    ]
    for bench_idx, (suffix, x, y) in enumerate(fixed_benches, start=1):
        add_fixed_bench(parts, f"fixed_student_bench_{suffix}", x, y)
        for chair_idx, dy in enumerate((-0.38, 0.38), start=1):
            add_plastic_wheel_chair(parts, f"plastic_wheel_chair_{bench_idx}_{chair_idx}", x + 0.62, y + dy, 3.1416)

    tall_table_rows = (8.05, 9.75, 11.45)
    tall_table_columns = (1.24, 2.12, 4.42, 5.30)
    tall_idx = 1
    for row_x in tall_table_rows:
        for col_y in tall_table_columns:
            add_mobile_table(parts, f"tall_mobile_table_{tall_idx}", row_x, col_y, 0.0)
            add_high_chair(parts, f"high_chair_{tall_idx}", row_x + 0.72, col_y, 3.1416)
            tall_idx += 1

    add_conveyor(parts, "conveyor_main", 17.20, 3.32, 0.0, length=4.20)
    add_conveyor(parts, "conveyor_return", 19.85, 4.12, 0.0, length=2.70)
    add_workcell(parts, "robot_workcell", 20.75, 2.02, 0.0)
    add_rack(parts, "mini_factory_rack", 18.20, 5.30, 0.0)
    add_cabinet(parts, "tool_cabinet_conveyor", 15.05, 5.34, 0.0, width=1.05)

    add_boxes(
        parts,
        "loose_box",
        (
            (16.30, 4.86, 0.22, 0.08, "box_cardboard"),
            (17.05, 4.92, 0.22, -0.12, "tote_orange"),
            (18.20, 5.30, 1.02, 0.0, "tote_gray"),
            (18.48, 5.30, 1.55, 0.0, "box_cardboard"),
            (20.92, 4.62, 0.48, 0.0, "tote_orange"),
            (21.42, 3.82, 0.22, 0.05, "box_cardboard"),
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
    pose_styles = {
        "red": {
            "left_arm": ((0.0, 0.23, 1.35), (0.10, 0.31, 1.12), (0.20, 0.25, 0.92)),
            "right_arm": ((0.0, -0.23, 1.35), (-0.08, -0.30, 1.11), (-0.18, -0.28, 0.90)),
            "left_leg": ((0.0, 0.08, 0.84), (0.08, 0.10, 0.47), (0.16, 0.09, 0.10)),
            "right_leg": ((0.0, -0.08, 0.84), (-0.06, -0.08, 0.47), (-0.13, -0.09, 0.10)),
            "left_foot_yaw": 0.10,
            "right_foot_yaw": -0.08,
        },
        "green": {
            "left_arm": ((0.0, 0.23, 1.35), (0.04, 0.34, 1.51), (0.02, 0.39, 1.70)),
            "right_arm": ((0.0, -0.23, 1.35), (0.04, -0.31, 1.12), (0.10, -0.28, 0.92)),
            "left_leg": ((0.0, 0.08, 0.84), (0.02, 0.10, 0.47), (0.04, 0.10, 0.10)),
            "right_leg": ((0.0, -0.08, 0.84), (-0.03, -0.10, 0.47), (-0.05, -0.10, 0.10)),
            "left_foot_yaw": 0.04,
            "right_foot_yaw": -0.05,
        },
        "blue": {
            "left_arm": ((0.0, 0.23, 1.35), (-0.08, 0.30, 1.11), (-0.18, 0.28, 0.91)),
            "right_arm": ((0.0, -0.23, 1.35), (0.11, -0.31, 1.13), (0.19, -0.25, 0.94)),
            "left_leg": ((0.0, 0.08, 0.84), (-0.07, 0.09, 0.47), (-0.15, 0.09, 0.10)),
            "right_leg": ((0.0, -0.08, 0.84), (0.09, -0.10, 0.47), (0.17, -0.10, 0.10)),
            "left_foot_yaw": -0.08,
            "right_foot_yaw": 0.10,
        },
        "yellow": {
            "left_arm": ((0.0, 0.23, 1.35), (-0.03, 0.31, 1.12), (-0.08, 0.28, 0.92)),
            "right_arm": ((0.0, -0.23, 1.35), (0.17, -0.28, 1.23), (0.31, -0.16, 1.14)),
            "left_leg": ((0.0, 0.08, 0.84), (-0.04, 0.13, 0.47), (-0.07, 0.16, 0.10)),
            "right_leg": ((0.0, -0.08, 0.84), (0.04, -0.13, 0.47), (0.07, -0.16, 0.10)),
            "left_foot_yaw": -0.18,
            "right_foot_yaw": 0.18,
        },
    }
    style = pose_styles[color_name]
    parts = [
        box_link("torso", (0, 0, 1.11, 0, 0, 0), (0.25, 0.34, 0.56), shirt),
        box_link("pelvis", (0, 0, 0.80, 0, 0, 0), (0.23, 0.28, 0.14), MATERIALS["pants"]),
        cylinder_between("shoulders", (0, -0.23, 1.36), (0, 0.23, 1.36), 0.055, shirt),
        cylinder_link("neck", (0, 0, 1.42, 0, 0, 0), 0.045, 0.13, MATERIALS["skin"], collision=False),
        sphere_link("head", (0, 0, 1.56, 0, 0, 0), 0.13, MATERIALS["skin"]),
        box_link("hair_cap", (-0.025, 0, 1.665, 0, 0, 0), (0.16, 0.22, 0.045), MATERIALS["hair"], collision=False),
        box_link("hair_back", (-0.07, 0, 1.59, 0, 0, 0), (0.055, 0.20, 0.12), MATERIALS["hair"], collision=False),
    ]
    for side in ("left", "right"):
        shoulder, elbow, hand = style[f"{side}_arm"]
        hip, knee, ankle = style[f"{side}_leg"]
        parts.extend(
            [
                cylinder_between(f"{side}_upper_arm", shoulder, elbow, 0.043, shirt),
                cylinder_between(f"{side}_forearm", elbow, hand, 0.034, MATERIALS["skin"]),
                sphere_link(f"{side}_hand", (*hand, 0, 0, 0), 0.043, MATERIALS["skin"]),
                cylinder_between(f"{side}_thigh", hip, knee, 0.055, MATERIALS["pants"]),
                cylinder_between(f"{side}_shin", knee, ankle, 0.048, MATERIALS["pants"]),
                box_link(
                    f"{side}_shoe",
                    (ankle[0] + 0.045, ankle[1], 0.04, 0, 0, style[f"{side}_foot_yaw"]),
                    (0.22, 0.10, 0.07),
                    MATERIALS["shoe"],
                ),
            ]
        )
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
        "Room 427 demo layout with teaching wall, projector screen, podium, classroom tables, aisle tape, and conveyor workcell props.",
    )
    for color_name in PERSON_SHIRTS:
        write_model(
            f"person_proxy_{color_name}",
            build_person_proxy_model(color_name),
            f"Local stylized standing person proxy with a {color_name} shirt for Gazebo tracking demos.",
        )


if __name__ == "__main__":
    main()
