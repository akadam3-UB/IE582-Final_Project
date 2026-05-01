#!/usr/bin/env python3
"""
Wall_generator_path_run.py

Path-style wall generator for Gazebo / Ignition.

This version does NOT force you to make rooms.
You define continuous wall paths/runs. Each path starts at a coordinate,
moves forward, and can turn left/right to continue from the same corner.

Run:
    python Wall_generator_path_run.py

Creates:
    models/fourth_floor_walls/model.config
    models/fourth_floor_walls/model.sdf

Coordinate system:
    Input is inches.
    SDF output is meters.
    x grows east/right.
    y grows north/up on plan.
    z grows upward.

Important:
    x0, y0 are WALL CENTERLINE coordinates.
    The wall is generated along its centerline.

Headings:
    "E" = +x
    "W" = -x
    "N" = +y
    "S" = -y

Commands:
    ("solid", L)
        Full-height wall for L inches.

    ("door", W)
        Door opening W inches wide with lintel/header above.

    ("door", W, H)
        Door opening W inches wide and H inches high.

    ("window", W, SILL, H)
        Window W inches wide.
        SILL is height from floor to bottom of window.
        H is window opening height.

    ("gap", W)
        Empty opening W inches wide. No wall, no lintel.

    ("move", W)
        Move forward W inches without making anything.
        Useful for shifting the drawing cursor.

    ("turn", "left")
    ("turn", "right")
    ("turn", "around")
        Change direction at the current point.

    ("heading", "N")
        Directly set heading.

    ("windows", COUNT, WINDOW_W, GAP, SILL, WINDOW_H, END_CAP)
        Repeated windows:
        END_CAP solid, window, GAP solid, window, ..., END_CAP solid.

        Example:
        ("windows", 8, 93, 26, 27, 38, 10)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


# ============================================================
# Global dimensions
# ============================================================

INCH = 0.0254

WALL_H_IN = 108.27
WALL_T_IN = 4.72
DEFAULT_DOOR_H_IN = 100

ADD_GLASS_PANES = True

ADD_FLOOR_SLAB = False
FLOOR_THICKNESS_IN = 1.0
FLOOR_MARGIN_IN = 24.0

WALL_COLOR = "0.82 0.82 0.82 1"
GLASS_COLOR = "0.35 0.65 0.95 0.35"
FLOOR_COLOR = "0.55 0.55 0.55 1"


# ============================================================
# EDIT THIS SECTION
# ============================================================
#
# Think of each path like drawing with a pen:
#
#   start at x0, y0
#   face heading
#   draw/move forward
#   turn
#   draw/move forward
#
# Use one path for one continuous maze/hallway wall.
# Use multiple paths only for disconnected walls.
# ============================================================

WALL_PATHS = [
    {
        "name": "Westbound wall from room",
        "x0": 0,
        "y0": 0,
        "heading": "W",
        "commands": [
            ("solid", 10),
            ("windows", 6, 93.25, 26.75, 43, 53, 0),
            ("solid", 10),
            ("turn", "right"),
            ("solid", 249),
            ("turn", "left"),
            ("solid", 12),
            ("turn", "right"),
            ("solid", 10),
            ("windows", 6, 93.25, 26.75, 43, 53, 0),
            ("solid", 10),
            ("turn", "right"),
            ("solid", 12),
            ("turn", "left"),
            ("solid", 260),
            ("turn", "right"),
            ("solid", 10),
            ("windows", 14, 93.25, 26.75, 43, 53, 0),
            ("solid", 10),
            ("turn", "right"),
            ("solid", 260),
            ("turn", "left"),
            ("windows", 1, 60, 0, 20, 80, 0),
            ("solid", 74),
            ("door", 36, 96),
        ],
    },
]

# Optional extra boxes: columns, protrusions, pilasters, etc.
# Coordinates are center coordinates in inches.
EXTRA_BOXES = [
    # {
    #     "name": "column_01",
    #     "x_center": 300,
    #     "y_center": 120,
    #     "sx": 12,
    #     "sy": 12,
    #     "height": WALL_H_IN,
    # },
]


# ============================================================
# Internal data
# ============================================================

def m(inches: float) -> float:
    return inches * INCH


@dataclass
class BoxPiece:
    name: str
    sx: float
    sy: float
    sz: float
    px: float
    py: float
    pz: float
    color: str
    collision: bool = True
    transparency: float | None = None


pieces: list[BoxPiece] = []


# ============================================================
# Geometry helpers
# ============================================================

def add_box(
    *,
    name: str,
    sx_in: float,
    sy_in: float,
    sz_in: float,
    px_in: float,
    py_in: float,
    pz_in: float,
    color: str = WALL_COLOR,
    collision: bool = True,
    transparency: float | None = None,
) -> None:
    pieces.append(
        BoxPiece(
            name=name,
            sx=m(sx_in),
            sy=m(sy_in),
            sz=m(sz_in),
            px=m(px_in),
            py=m(py_in),
            pz=m(pz_in),
            color=color,
            collision=collision,
            transparency=transparency,
        )
    )


def heading_vector(heading: str) -> tuple[int, int]:
    heading = heading.upper()
    if heading == "E":
        return 1, 0
    if heading == "W":
        return -1, 0
    if heading == "N":
        return 0, 1
    if heading == "S":
        return 0, -1
    raise ValueError(f"Invalid heading {heading!r}. Use E, W, N, or S.")


def turn_heading(heading: str, turn: str) -> str:
    heading = heading.upper()
    turn = str(turn).lower()

    headings = ["E", "N", "W", "S"]  # left turn advances index
    if heading not in headings:
        raise ValueError(f"Invalid heading {heading!r}.")

    idx = headings.index(heading)

    if turn in ("left", "l", "+90", "90"):
        return headings[(idx + 1) % 4]
    if turn in ("right", "r", "-90"):
        return headings[(idx - 1) % 4]
    if turn in ("around", "back", "180"):
        return headings[(idx + 2) % 4]

    raise ValueError(f"Invalid turn {turn!r}. Use left, right, or around.")


def segment_pose_from_start(
    *,
    x: float,
    y: float,
    heading: str,
    length: float,
) -> tuple[float, float, float, float, float, float]:
    """
    Given current point and heading, return:
        px, py, sx, sy, next_x, next_y

    All values are in inches.
    """
    dx, dy = heading_vector(heading)

    next_x = x + dx * length
    next_y = y + dy * length

    px = (x + next_x) / 2.0
    py = (y + next_y) / 2.0

    if dx != 0:
        sx = length
        sy = WALL_T_IN
    else:
        sx = WALL_T_IN
        sy = length

    return px, py, sx, sy, next_x, next_y


def add_full_height_segment(
    *,
    name: str,
    x: float,
    y: float,
    heading: str,
    length: float,
) -> tuple[float, float]:
    px, py, sx, sy, next_x, next_y = segment_pose_from_start(
        x=x,
        y=y,
        heading=heading,
        length=length,
    )

    add_box(
        name=name,
        sx_in=sx,
        sy_in=sy,
        sz_in=WALL_H_IN,
        px_in=px,
        py_in=py,
        pz_in=WALL_H_IN / 2.0,
    )

    return next_x, next_y


def add_door_segment(
    *,
    name: str,
    x: float,
    y: float,
    heading: str,
    width: float,
    door_h: float,
) -> tuple[float, float]:
    lintel_h = WALL_H_IN - door_h

    px, py, sx, sy, next_x, next_y = segment_pose_from_start(
        x=x,
        y=y,
        heading=heading,
        length=width,
    )

    if lintel_h > 0:
        add_box(
            name=name,
            sx_in=sx,
            sy_in=sy,
            sz_in=lintel_h,
            px_in=px,
            py_in=py,
            pz_in=door_h + lintel_h / 2.0,
        )

    return next_x, next_y


def add_window_segment(
    *,
    name: str,
    x: float,
    y: float,
    heading: str,
    width: float,
    sill_h: float,
    window_h: float,
) -> tuple[float, float]:
    upper_h = WALL_H_IN - sill_h - window_h

    if sill_h <= 0:
        raise ValueError(f"{name}: sill height must be positive.")
    if window_h <= 0:
        raise ValueError(f"{name}: window height must be positive.")
    if upper_h <= 0:
        raise ValueError(f"{name}: sill + window height exceeds wall height.")

    px, py, sx, sy, next_x, next_y = segment_pose_from_start(
        x=x,
        y=y,
        heading=heading,
        length=width,
    )

    # Lower wall under the window.
    add_box(
        name=f"{name}_lower",
        sx_in=sx,
        sy_in=sy,
        sz_in=sill_h,
        px_in=px,
        py_in=py,
        pz_in=sill_h / 2.0,
    )

    # Upper wall above the window.
    add_box(
        name=f"{name}_upper",
        sx_in=sx,
        sy_in=sy,
        sz_in=upper_h,
        px_in=px,
        py_in=py,
        pz_in=sill_h + window_h + upper_h / 2.0,
    )

    # Optional visual-only glass pane.
    if ADD_GLASS_PANES:
        glass_t = min(1.0, WALL_T_IN * 0.20)

        dx, dy = heading_vector(heading)
        if dx != 0:
            glass_sx = width
            glass_sy = glass_t
        else:
            glass_sx = glass_t
            glass_sy = width

        add_box(
            name=f"{name}_glass_visual",
            sx_in=glass_sx,
            sy_in=glass_sy,
            sz_in=window_h,
            px_in=px,
            py_in=py,
            pz_in=sill_h + window_h / 2.0,
            color=GLASS_COLOR,
            collision=False,
            transparency=0.55,
        )

    return next_x, next_y


def expand_windows_command(cmd: tuple) -> list[tuple]:
    """
    Convert:
        ("windows", count, window_w, gap, sill, window_h, end_cap)

    Into:
        solid end_cap, window, solid gap, window, ..., solid end_cap
    """
    _, count, window_w, gap, sill, window_h, end_cap = cmd

    count = int(count)
    window_w = float(window_w)
    gap = float(gap)
    sill = float(sill)
    window_h = float(window_h)
    end_cap = float(end_cap)

    expanded: list[tuple] = []

    if end_cap > 0:
        expanded.append(("solid", end_cap))

    for i in range(count):
        expanded.append(("window", window_w, sill, window_h))
        if i < count - 1 and gap > 0:
            expanded.append(("solid", gap))

    if end_cap > 0:
        expanded.append(("solid", end_cap))

    return expanded


def run_wall_path(path: dict) -> tuple[float, float, str, float]:
    """
    Generate one continuous path.

    Returns:
        final_x, final_y, final_heading, total_forward_length
    """
    name = path["name"]
    x = float(path["x0"])
    y = float(path["y0"])
    heading = str(path["heading"]).upper()

    total_forward_length = 0.0
    command_index = 0

    for raw_cmd in path["commands"]:
        # Expand repeated window command into normal commands.
        if raw_cmd[0] == "windows":
            commands = expand_windows_command(raw_cmd)
        else:
            commands = [raw_cmd]

        for cmd in commands:
            command_index += 1
            kind = cmd[0]

            if kind in ("solid", "wall", "post"):
                length = float(cmd[1])
                x, y = add_full_height_segment(
                    name=f"{name}_{command_index:03d}_{kind}",
                    x=x,
                    y=y,
                    heading=heading,
                    length=length,
                )
                total_forward_length += length

            elif kind == "door":
                width = float(cmd[1])
                door_h = float(cmd[2]) if len(cmd) >= 3 else DEFAULT_DOOR_H_IN
                x, y = add_door_segment(
                    name=f"{name}_{command_index:03d}_door_lintel",
                    x=x,
                    y=y,
                    heading=heading,
                    width=width,
                    door_h=door_h,
                )
                total_forward_length += width

            elif kind == "window":
                width = float(cmd[1])
                sill_h = float(cmd[2])
                window_h = float(cmd[3])
                x, y = add_window_segment(
                    name=f"{name}_{command_index:03d}_window",
                    x=x,
                    y=y,
                    heading=heading,
                    width=width,
                    sill_h=sill_h,
                    window_h=window_h,
                )
                total_forward_length += width

            elif kind == "gap":
                width = float(cmd[1])
                dx, dy = heading_vector(heading)
                x += dx * width
                y += dy * width
                total_forward_length += width

            elif kind == "move":
                width = float(cmd[1])
                dx, dy = heading_vector(heading)
                x += dx * width
                y += dy * width

            elif kind == "turn":
                heading = turn_heading(heading, cmd[1])

            elif kind == "heading":
                heading = str(cmd[1]).upper()
                heading_vector(heading)  # validate

            else:
                raise ValueError(f"{name}: unknown command {kind!r}")

    return x, y, heading, total_forward_length


def add_extra_boxes() -> None:
    for box in EXTRA_BOXES:
        height = float(box.get("height", WALL_H_IN))

        add_box(
            name=box["name"],
            sx_in=float(box["sx"]),
            sy_in=float(box["sy"]),
            sz_in=height,
            px_in=float(box["x_center"]),
            py_in=float(box["y_center"]),
            pz_in=height / 2.0,
            color=box.get("color", WALL_COLOR),
            collision=box.get("collision", True),
            transparency=box.get("transparency", None),
        )


def compute_plan_bounds_in() -> tuple[float, float, float, float]:
    if not pieces:
        return 0.0, 0.0, 0.0, 0.0

    min_x = min((p.px - p.sx / 2.0) / INCH for p in pieces)
    max_x = max((p.px + p.sx / 2.0) / INCH for p in pieces)
    min_y = min((p.py - p.sy / 2.0) / INCH for p in pieces)
    max_y = max((p.py + p.sy / 2.0) / INCH for p in pieces)

    return min_x, max_x, min_y, max_y


def add_floor_slab_from_bounds() -> None:
    min_x, max_x, min_y, max_y = compute_plan_bounds_in()

    min_x -= FLOOR_MARGIN_IN
    max_x += FLOOR_MARGIN_IN
    min_y -= FLOOR_MARGIN_IN
    max_y += FLOOR_MARGIN_IN

    add_box(
        name="floor_slab",
        sx_in=max_x - min_x,
        sy_in=max_y - min_y,
        sz_in=FLOOR_THICKNESS_IN,
        px_in=(min_x + max_x) / 2.0,
        py_in=(min_y + max_y) / 2.0,
        pz_in=-FLOOR_THICKNESS_IN / 2.0,
        color=FLOOR_COLOR,
        collision=True,
    )


def build_model() -> None:
    pieces.clear()

    print("Wall path checks:")
    for path in WALL_PATHS:
        final_x, final_y, final_heading, total_len = run_wall_path(path)
        print(
            f"  {path['name']}: total drawn/moved length = {total_len:.3f} in, "
            f"end = ({final_x:.3f}, {final_y:.3f}), heading = {final_heading}"
        )

    add_extra_boxes()

    if ADD_FLOOR_SLAB:
        add_floor_slab_from_bounds()


# ============================================================
# SDF writing
# ============================================================

def box_xml(p: BoxPiece) -> str:
    collision_xml = ""
    if p.collision:
        collision_xml = f"""
      <collision name="{p.name}_collision">
        <geometry>
          <box>
            <size>{p.sx:.4f} {p.sy:.4f} {p.sz:.4f}</size>
          </box>
        </geometry>
      </collision>
"""

    transparency_xml = ""
    if p.transparency is not None:
        transparency_xml = f"""
          <transparency>{p.transparency:.3f}</transparency>
"""

    return f"""
    <link name="{p.name}">
      <pose>{p.px:.4f} {p.py:.4f} {p.pz:.4f} 0 0 0</pose>
{collision_xml}
      <visual name="{p.name}_visual">
        <geometry>
          <box>
            <size>{p.sx:.4f} {p.sy:.4f} {p.sz:.4f}</size>
          </box>
        </geometry>
        <material>
          <ambient>{p.color}</ambient>
          <diffuse>{p.color}</diffuse>
{transparency_xml}
        </material>
      </visual>
    </link>
"""


def make_model_config() -> str:
    return """<?xml version="1.0"?>
<model>
  <name>fourth_floor_walls</name>
  <version>1.0</version>
  <sdf version="1.10">model.sdf</sdf>

  <author>
    <name>Abhijeet Kadam</name>
    <email>akadam3@buffalo.edu</email>
  </author>

  <description>
    Fourth-floor wall layout generated from continuous wall paths.
  </description>
</model>
"""


def make_model_sdf() -> str:
    return f"""<?xml version="1.0"?>
<sdf version="1.10">
  <model name="fourth_floor_walls">
    <static>true</static>
{chr(10).join(box_xml(p) for p in pieces)}
  </model>
</sdf>
"""


def write_model(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "model.config").write_text(make_model_config(), encoding="utf-8")
    (output_dir / "model.sdf").write_text(make_model_sdf(), encoding="utf-8")

    print()
    print("Created:")
    print(f"  {output_dir / 'model.config'}")
    print(f"  {output_dir / 'model.sdf'}")
    print()
    print(f"Pieces generated: {len(pieces)}")
    print()
    print("World include:")
    print("""
    <include>
      <uri>model://fourth_floor_walls</uri>
      <pose>0 0 0 0 0 0</pose>
    </include>
""")


def main() -> None:
    build_model()
    write_model(Path("models/fourth_floor_walls"))


if __name__ == "__main__":
    main()
