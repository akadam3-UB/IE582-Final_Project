#!/usr/bin/env python3
"""
generate_fourth_floor_walls_clean.py

General fourth-floor wall generator for Gazebo / Ignition.

Use this file directly:
    python generate_fourth_floor_walls_clean.py

It creates:
    models/fourth_floor_walls/model.config
    models/fourth_floor_walls/model.sdf

How walls work:
    ("solid", L)              full-height wall for L inches
    ("door", W)               door opening W inches wide with lintel above
    ("door", W, H)            door opening W inches wide and H inches high
    ("gap", W)                completely open gap, no lintel
    ("window", W, SILL, H)    window W wide, sill height SILL, window height H

Coordinate convention:
    Input coordinates are inches.
    Output SDF dimensions are meters.
    x grows right.
    y grows up on the floor plan.
    z grows upward.
    Wall start point is wall CENTERLINE start.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


# ============================================================
# Global constants
# ============================================================

INCH = 0.0254

WALL_H_IN = 113
WALL_T_IN = 12
HALF_WALL_T_IN = WALL_T_IN / 2.0

DEFAULT_DOOR_H_IN = 100

ADD_GLASS_PANES = True
ADD_FLOOR_SLAB = True
FLOOR_THICKNESS_IN = 1.0
FLOOR_MARGIN_IN = 24.0

WALL_COLOR = "0.82 0.82 0.82 1"
GLASS_COLOR = "0.35 0.65 0.95 0.35"
FLOOR_COLOR = "0.55 0.55 0.55 1"


# ============================================================
# Convenience helpers for repeated window walls
# ============================================================

def repeated_window_segments(
    *,
    total_len_in: float,
    count: int,
    window_w_in: float = 93,
    gap_in: float = 26,
    sill_in: float = 27,
    window_h_in: float = 38,
    end_cap_in: float | None = None,
) -> list[tuple]:
    """
    Build repeated window segments that exactly fit a wall length.

    If end_cap_in is None:
        end caps are calculated equally:
        end_cap = (total_len - count*window_w - (count-1)*gap) / 2

    If end_cap_in is given:
        it uses that value at both ends and prints no automatic adjustment.

    Pattern:
        end cap | window | gap/post | window | ... | end cap
    """
    if count <= 0:
        return [("solid", total_len_in)]

    fixed_middle = count * window_w_in + (count - 1) * gap_in

    if end_cap_in is None:
        end_cap = (total_len_in - fixed_middle) / 2.0
    else:
        end_cap = float(end_cap_in)

    if end_cap < 0:
        raise ValueError(
            f"Windows do not fit. total_len={total_len_in}, "
            f"count={count}, window_w={window_w_in}, gap={gap_in}. "
            f"Need at least {fixed_middle} inches before end caps."
        )

    segments: list[tuple] = []

    if end_cap > 0:
        segments.append(("solid", end_cap))

    for i in range(count):
        segments.append(("window", window_w_in, sill_in, window_h_in))

        if i < count - 1 and gap_in > 0:
            segments.append(("solid", gap_in))

    if end_cap > 0:
        segments.append(("solid", end_cap))

    return segments


def rectangle_room_walls(
    *,
    name: str,
    x0_in: float,
    y0_in: float,
    length_in: float,
    depth_in: float,
    south_windows: int = 0,
    north_windows: int = 0,
    west_windows: int = 0,
    east_windows: int = 0,
    south_segments: list[tuple] | None = None,
    north_segments: list[tuple] | None = None,
    west_segments: list[tuple] | None = None,
    east_segments: list[tuple] | None = None,
) -> list[dict]:
    """
    Create four wall runs for a rectangular room.

    x0_in, y0_in = inside bottom-left corner of the room.
    length_in = inside length in x direction.
    depth_in = inside depth in y direction.

    Wall centerlines are automatically shifted by half wall thickness.
    """
    if south_segments is None:
        south_segments = repeated_window_segments(total_len_in=length_in, count=south_windows)

    if north_segments is None:
        north_segments = repeated_window_segments(total_len_in=length_in, count=north_windows)

    if west_segments is None:
        west_segments = repeated_window_segments(total_len_in=depth_in, count=west_windows)

    if east_segments is None:
        east_segments = repeated_window_segments(total_len_in=depth_in, count=east_windows)

    return [
        {
            "name": f"{name}_south_wall",
            "x0": x0_in,
            "y0": y0_in - HALF_WALL_T_IN,
            "orientation": "x",
            "segments": south_segments,
        },
        {
            "name": f"{name}_north_wall",
            "x0": x0_in,
            "y0": y0_in + depth_in + HALF_WALL_T_IN,
            "orientation": "x",
            "segments": north_segments,
        },
        {
            "name": f"{name}_west_wall",
            "x0": x0_in - HALF_WALL_T_IN,
            "y0": y0_in,
            "orientation": "y",
            "segments": west_segments,
        },
        {
            "name": f"{name}_east_wall",
            "x0": x0_in + length_in + HALF_WALL_T_IN,
            "y0": y0_in,
            "orientation": "y",
            "segments": east_segments,
        },
    ]


# ============================================================
# EDIT THIS SECTION
# ============================================================

# Example room based on your Room 427 dimensions.
# South wall has 8 windows.
# East/right wall has 2 windows.
# West/left wall has 6 windows.
# North wall has two doors like your earlier top wall.
#
# IMPORTANT:
# If 6 windows do not physically fit on the west side, this file will throw
# a clear error. Then either increase room depth or reduce window width/gap/count.

ROOM_427_X0_IN = 0
ROOM_427_Y0_IN = 0
ROOM_427_LEN_IN = 941
ROOM_427_DEP_IN = 941  # Change this to the real depth if the left side has 6 windows.

FOURTH_FLOOR_WALLS: list[dict] = []

FOURTH_FLOOR_WALLS += rectangle_room_walls(
    name="room_427",
    x0_in=ROOM_427_X0_IN,
    y0_in=ROOM_427_Y0_IN,
    length_in=ROOM_427_LEN_IN,
    depth_in=ROOM_427_DEP_IN,

    # Window counts
    south_windows=8,
    east_windows=2,
    west_windows=6,

    # North/back wall can be customized with doors.
    # If this is just a solid wall, replace with [("solid", ROOM_427_LEN_IN)].
    north_segments=[
        ("solid", 480),
        ("door", 72),
        ("solid", 164),
        ("door", 72),
        ("solid", 153),
    ],
)

# Add more fourth-floor hallway or room walls here:
#
# FOURTH_FLOOR_WALLS.append({
#     "name": "hallway_wall_01",
#     "x0": 0,
#     "y0": 1200,
#     "orientation": "x",
#     "segments": [
#         ("solid", 180),
#         ("door", 36),
#         ("solid", 220),
#         ("gap", 72),
#         ("solid", 140),
#     ],
# })


# Optional columns/protrusions/extra boxes.
# Each box uses center coordinates in inches.
EXTRA_BOXES = [
    {
        "name": "room_427_top_protrusion_1",
        "x_center": 258 + 6 / 2,
        "y_center": ROOM_427_DEP_IN - 56 / 2,
        "sx": 6,
        "sy": 56,
        "height": WALL_H_IN,
    },
    {
        "name": "room_427_top_protrusion_2",
        "x_center": 316 + 6 / 2,
        "y_center": ROOM_427_DEP_IN - 56 / 2,
        "sx": 6,
        "sy": 56,
        "height": WALL_H_IN,
    },
    {
        "name": "room_427_top_protrusion_3",
        "x_center": 376 + 6 / 2,
        "y_center": ROOM_427_DEP_IN - 56 / 2,
        "sx": 6,
        "sy": 56,
        "height": WALL_H_IN,
    },
    {
        "name": "room_427_top_protrusion_4",
        "x_center": 433 + 6 / 2,
        "y_center": ROOM_427_DEP_IN - 56 / 2,
        "sx": 6,
        "sy": 56,
        "height": WALL_H_IN,
    },
]


# ============================================================
# Generator internals
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


def piece_pose_for_segment(
    orientation: Literal["x", "y"],
    x0: float,
    y0: float,
    cursor: float,
    length: float,
) -> tuple[float, float, float, float]:
    if orientation == "x":
        return x0 + cursor + length / 2.0, y0, length, WALL_T_IN
    if orientation == "y":
        return x0, y0 + cursor + length / 2.0, WALL_T_IN, length

    raise ValueError(f"Invalid orientation {orientation!r}. Use 'x' or 'y'.")


def add_full_height_segment(
    *,
    name: str,
    orientation: Literal["x", "y"],
    x0: float,
    y0: float,
    cursor: float,
    length: float,
) -> None:
    px, py, sx, sy = piece_pose_for_segment(orientation, x0, y0, cursor, length)

    add_box(
        name=name,
        sx_in=sx,
        sy_in=sy,
        sz_in=WALL_H_IN,
        px_in=px,
        py_in=py,
        pz_in=WALL_H_IN / 2.0,
    )


def add_door_segment(
    *,
    name: str,
    orientation: Literal["x", "y"],
    x0: float,
    y0: float,
    cursor: float,
    width: float,
    door_h: float,
) -> None:
    lintel_h = WALL_H_IN - door_h

    if lintel_h <= 0:
        return

    px, py, sx, sy = piece_pose_for_segment(orientation, x0, y0, cursor, width)

    add_box(
        name=name,
        sx_in=sx,
        sy_in=sy,
        sz_in=lintel_h,
        px_in=px,
        py_in=py,
        pz_in=door_h + lintel_h / 2.0,
    )


def add_window_segment(
    *,
    name: str,
    orientation: Literal["x", "y"],
    x0: float,
    y0: float,
    cursor: float,
    width: float,
    sill_h: float,
    window_h: float,
) -> None:
    upper_h = WALL_H_IN - sill_h - window_h

    if sill_h <= 0:
        raise ValueError(f"{name}: sill height must be positive.")
    if window_h <= 0:
        raise ValueError(f"{name}: window height must be positive.")
    if upper_h <= 0:
        raise ValueError(f"{name}: sill + window is taller than wall height.")

    px, py, sx, sy = piece_pose_for_segment(orientation, x0, y0, cursor, width)

    add_box(
        name=f"{name}_lower",
        sx_in=sx,
        sy_in=sy,
        sz_in=sill_h,
        px_in=px,
        py_in=py,
        pz_in=sill_h / 2.0,
    )

    add_box(
        name=f"{name}_upper",
        sx_in=sx,
        sy_in=sy,
        sz_in=upper_h,
        px_in=px,
        py_in=py,
        pz_in=sill_h + window_h + upper_h / 2.0,
    )

    if ADD_GLASS_PANES:
        glass_t = min(1.0, WALL_T_IN * 0.20)

        if orientation == "x":
            glass_sx, glass_sy = width, glass_t
        else:
            glass_sx, glass_sy = glass_t, width

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


def add_wall_run(wall: dict) -> float:
    name = wall["name"]
    x0 = float(wall["x0"])
    y0 = float(wall["y0"])
    orientation = wall["orientation"]

    if orientation not in ("x", "y"):
        raise ValueError(f"{name}: orientation must be 'x' or 'y'.")

    cursor = 0.0

    for i, seg in enumerate(wall["segments"], start=1):
        kind = seg[0]

        if kind in ("solid", "post"):
            length = float(seg[1])
            add_full_height_segment(
                name=f"{name}_{i:03d}_{kind}",
                orientation=orientation,
                x0=x0,
                y0=y0,
                cursor=cursor,
                length=length,
            )
            cursor += length

        elif kind == "door":
            width = float(seg[1])
            door_h = float(seg[2]) if len(seg) >= 3 else DEFAULT_DOOR_H_IN
            add_door_segment(
                name=f"{name}_{i:03d}_door_lintel",
                orientation=orientation,
                x0=x0,
                y0=y0,
                cursor=cursor,
                width=width,
                door_h=door_h,
            )
            cursor += width

        elif kind == "window":
            width = float(seg[1])
            sill_h = float(seg[2])
            window_h = float(seg[3])
            add_window_segment(
                name=f"{name}_{i:03d}_window",
                orientation=orientation,
                x0=x0,
                y0=y0,
                cursor=cursor,
                width=width,
                sill_h=sill_h,
                window_h=window_h,
            )
            cursor += width

        elif kind == "gap":
            cursor += float(seg[1])

        else:
            raise ValueError(f"{name}: unknown segment kind {kind!r}")

    return cursor


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


def build_fourth_floor() -> None:
    pieces.clear()

    print("Wall run length checks:")
    for wall in FOURTH_FLOOR_WALLS:
        length = add_wall_run(wall)
        print(f"  {wall['name']}: {length:.3f} in")

    add_extra_boxes()

    if ADD_FLOOR_SLAB:
        add_floor_slab_from_bounds()


# ============================================================
# SDF output
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
    Fourth-floor wall layout generated from editable wall runs.
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

    model_config_path = output_dir / "model.config"
    model_sdf_path = output_dir / "model.sdf"

    model_config_path.write_text(make_model_config(), encoding="utf-8")
    model_sdf_path.write_text(make_model_sdf(), encoding="utf-8")

    print()
    print("Created:")
    print(f"  {model_config_path}")
    print(f"  {model_sdf_path}")
    print()
    print(f"Pieces generated: {len(pieces)}")
    print()
    print("Include this in your world:")
    print("""
    <include>
      <uri>model://fourth_floor_walls</uri>
      <pose>0 0 0 0 0 0</pose>
    </include>
""")


def main() -> None:
    build_fourth_floor()
    write_model(Path("models/fourth_floor_walls"))


if __name__ == "__main__":
    main()
