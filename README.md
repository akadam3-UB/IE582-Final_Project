# IE582 Room 427 Pan/Tilt Tracking

Text- or speech-guided pan/tilt camera tracking in a Gazebo model of Room 427.

The project answers one focused question:

> Given a command such as `track the red person`, can the system choose the intended target and move a pan/tilt camera to keep that target centered?

The repository is intentionally small enough for an Industrial Engineering student with moderate programming experience to extend.

## What Is Included

- A detailed Room 427 Gazebo world with walls, windows, glossy floor, lights, tables, chairs, cabinets, yellow floor tape, racks, boxes, workcell-style props, and colored people.
- A command parser for simple instructions such as `track the red person`, `track the person on the left`, and `stop`.
- Optional VLM JSON grounding for richer target descriptions.
- A target selector that ranks detections by command match, confidence, center distance, target size, and sticky target preference.
- A pan/tilt controller that converts image error into bounded joint commands.
- A stable Gazebo pose-based demo that avoids local camera-rendering issues.
- Optional speech, camera-detection, and class-host bridges for advanced experiments.
- Unit tests for the parser, selector, controller, runtime input handling, vision utilities, and pipeline.

## Repository Map

```text
Simulation/
  Models/                         Gazebo model assets used by Room 427
  worlds/room_427.world           Room 427 scene for visual inspection
  worlds/room_427_tracking_test.world
                                   Room 427 scene with a pan/tilt camera
  generate_room_427_furnishings.py
                                   Rebuilds generated classroom/lab props
scripts/
  run_gazebo_room_427_world.sh     Open the room
  run_gazebo_room_427_tracking_world_gui.sh
                                   Open room + camera GUI
  run_gazebo_room_427_tracking_world.sh
                                   Open tracking world server only
  run_gazebo_room_427_camera_view.sh
                                   Open only the pan/tilt camera POV
  run_gazebo_room_427_pose_tracker.sh
                                   Run the stable Gazebo pose tracker
  pan_tilt_gazebo_pose_tracker.py  Pose-topic demo tracker
  pan_tilt_gazebo_tracker.py       Optional camera/YOLO tracker
  mic_command_listener.py          Optional microphone-to-command bridge
  pan_tilt_socket_client.py        Optional class host bridge
  demo_pan_tilt_pipeline.py        Small parser/selector/controller demo
src/ie582_final_project/
  command_parser.py
  target_selector.py
  pan_tilt_controller.py
  pan_tilt_pipeline.py
  runtime_inputs.py
  vision.py
tests/
docs/
```

## Quick Start

From the project root:

```bash
python3 -m pip install -e .
```

```bash
python3 -m unittest discover -s tests -v
```

Open the Room 427 scene:

```bash
./scripts/run_gazebo_room_427_world.sh
```

Run the tracking demo:

```bash
./scripts/run_gazebo_room_427_tracking_world_gui.sh
```

In a second terminal:

```bash
echo "track the red person" > runtime_command.txt
./scripts/run_gazebo_room_427_pose_tracker.sh
```

Try other commands while the tracker is running:

```bash
echo "track the blue person on the right" > runtime_command.txt
echo "track the green person in the center" > runtime_command.txt
echo "track the yellow person" > runtime_command.txt
echo "stop" > runtime_command.txt
```

On Apple Silicon, the launch scripts default to Metal rendering and set `GZ_RELAY=127.0.0.1` so Gazebo GUI, pose topics, and tracker commands can discover each other locally.

### Two-Window Demo Layout

For a cleaner presentation, run the simulator once, then open separate windows for the world and the camera POV.

Terminal 1:

```bash
./scripts/run_gazebo_room_427_tracking_world.sh
```

Terminal 2, world view:

```bash
gz sim -g
```

Terminal 3, pan/tilt camera POV:

```bash
./scripts/run_gazebo_room_427_camera_view.sh
```

Terminal 4, tracking:

```bash
echo "track the red person" > runtime_command.txt
./scripts/run_gazebo_room_427_pose_tracker.sh
```

Move the world-view GUI and camera-POV GUI onto different screens. The camera POV comes from the sensor topic `/world/room_427_tracking_test/model/pantilt/link/tilt_link/sensor/camera/image`.

## Optional Advanced Paths

The stable path above is the one to demo first. The repo also keeps a few higher-risk extension paths because they are useful for the original project scope:

- `scripts/mic_command_listener.py` records short macOS microphone clips and writes transcribed text into `runtime_command.txt`.
- `scripts/pan_tilt_gazebo_tracker.py` uses the Gazebo camera image topic plus Ultralytics tracking instead of ground-truth poses.
- `scripts/pan_tilt_socket_client.py` is a bridge toward the class host socket protocol.

These paths may require local packages such as `opencv-python`, `ultralytics`, `mlx-whisper`, `openai-whisper`, `python-socketio`, or course-specific `ub_camera` utilities. Keep those dependencies and model weights local; do not commit `.pt` files or virtual environments.

Example optional installs:

```bash
python3 -m pip install -e ".[vision]"
python3 -m pip install -e ".[speech]"
```

## Room 427 Scene

The room scene is generated from [Simulation/generate_room_427_furnishings.py](Simulation/generate_room_427_furnishings.py). To rebuild it after editing the layout:

```bash
python3 Simulation/generate_room_427_furnishings.py
xmllint --noout Simulation/Models/room_427_furnishings/model.sdf
```

The current scene intentionally does **not** include the middle conveyor. It keeps the classroom/lab feel with tables, chairs, cabinets, racks, boxes, workcell props, floor tape, blinds, and people.

## How To Extend

Good first changes:

1. Move people or furniture in `Simulation/worlds/room_427_tracking_test.world`.
2. Add a new color/person proxy in `Simulation/generate_room_427_furnishings.py`.
3. Add command words in `src/ie582_final_project/command_parser.py`.
4. Tune selection weights in `src/ie582_final_project/target_selector.py`.
5. Tune camera motion in `src/ie582_final_project/pan_tilt_controller.py`.
6. Try the optional camera tracker after the pose tracker is stable.
7. Add or update tests in `tests/`.

Keep changes small and test after each one.

## Notes For Hosting

The repo avoids committing local virtual environments, Python caches, package build metadata, logs, and model weight files. Keep the stable Room 427 path easy to run, and treat speech/camera/host integrations as optional extensions with clearly documented dependencies.
