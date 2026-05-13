# Speech-Guided Pan/Tilt Target Tracking System

Team Member:
- Abhijeet Kadam, akadam3@buffalo.edu

## Project Objective

Build a command-guided pan/tilt camera system in a Gazebo model of Room 427. Given a command such as `track the red person` or `track the person on the left`, the system should select the intended target and move the pan/tilt camera so that target stays centered.

The stable final demo uses Gazebo model poses for repeatability. The repository also preserves optional speech, camera-detection, VLM-grounding, and class-host paths so the project can be extended toward the original speech-guided vision goal.

## Current System

1. Room 427 Gazebo world with walls, windows, floor tape, tables, chairs, cabinets, racks, boxes, workcell props, and colored people.
2. Rule-based command parser with optional VLM JSON override.
3. Target selector using label, color, left/center/right region, confidence, target size, center distance, and sticky target preference.
4. Pan/tilt controller with deadband, rate limit, and joint limits.
5. Stable Gazebo pose tracker for the final demo.
6. Optional camera/YOLO tracker, microphone command bridge, and class host socket bridge.

## Design Contribution

The project adds an intent-resolution layer between human commands and visual servoing. A basic tracker can follow an already-known target; this system decides which target should be followed when several valid candidates are visible.

The main engineering idea is to keep the fast control loop simple and explainable while allowing slower grounding inputs to refine the command only when needed.

## Primary Demo Path

Use this path first because it is deterministic and avoids local rendering/model issues:

```bash
./scripts/run_gazebo_room_427_tracking_world_gui.sh
```

In a second terminal:

```bash
echo "track the red person" > runtime_command.txt
./scripts/run_gazebo_room_427_pose_tracker.sh
```

## Optional Extensions

- `scripts/mic_command_listener.py`: records short microphone clips and writes commands to `runtime_command.txt`.
- `scripts/pan_tilt_gazebo_tracker.py`: uses Gazebo camera frames plus Ultralytics detections.
- `scripts/pan_tilt_socket_client.py`: adapts the pipeline to the class host socket protocol.
- `src/ie582_final_project/vision.py`: converts detector outputs into project detections and estimates simple color attributes.

These extensions may require local packages and model weights. They should remain optional so the hosted repository stays runnable without large binary files.

## Measures Of Success

- Correct target is selected for commands involving color, region, class, or track ID.
- The selected target stays stable instead of switching unnecessarily.
- Pan/tilt commands stay inside limits and do not jump abruptly.
- The stable Room 427 demo can be run from the README.
- Optional speech and camera paths can be developed without changing the core parser, selector, or controller.
