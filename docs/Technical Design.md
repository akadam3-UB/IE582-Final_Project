# Technical Design

## Project Boundary

This project is a Room 427 pan/tilt camera demo. It is not a mobile robot, path planner, or full building simulation.

The system does four things:

1. parse a command such as `track the red person`
2. rank visible targets against that command
3. keep the selected target stable across frames
4. publish pan/tilt joint commands that move the camera toward the target center

## Data Flow

```text
command text
  -> command_parser.py
  -> CommandIntent

optional speech/audio or VLM JSON
  -> runtime_inputs.py
  -> command_parser.py

detections from camera pixels
  -> target_selector.py
  -> ranked TargetScore list

best target + current joint state
  -> pan_tilt_controller.py
  -> PanTiltCommand
```

`pan_tilt_pipeline.py` ties these pieces together and remembers the active target so the camera does not jump between similar people.

## Main Runtime Paths

### Primary Gazebo Camera Demo

Use this first:

```bash
./scripts/run_gazebo_room_427_tracking_world.sh
gz sim -g
./scripts/run_gazebo_room_427_camera_view.sh
echo "track the red person" > runtime_command.txt
./scripts/run_gazebo_room_427_camera_tracker.sh
```

This path uses the Gazebo camera image topic from the original `model://pantilt` camera mounted near the ceiling at Room 427 center. The default detector is `color-proxy`, which thresholds the staged red, green, blue, and yellow people from real rendered pixels and passes those detections through the normal selector and controller.

### Debug And Advanced Paths

Keep these behind the camera demo:

- `mic_command_listener.py` can write spoken commands into `runtime_command.txt`.
- `pan_tilt_gazebo_tracker.py --detector yolo` uses the Gazebo camera image topic and Ultralytics detections.
- `pan_tilt_gazebo_pose_tracker.py` reads Gazebo model poses for deterministic debugging. It is not the main perception demo because it bypasses the camera image.
- `pan_tilt_socket_client.py` adapts the same parser, selector, and controller to the class host socket protocol.
- `vision.py` converts detector outputs into the common `Detection` model and estimates simple color attributes from image crops.

These paths preserve the original speech/vision project complexity, but they should not block the Room 427 camera demo.

## Important Design Choices

### Heuristic Target Selection

The selector uses weighted signals instead of a learned policy:

- target label match
- color match
- left/center/right region match
- confidence
- image-center distance
- target size
- sticky target bonus

This keeps behavior explainable for a semester project and makes debugging easier.

### Sticky Targeting

Once a target is selected, the pipeline gives it a small bonus. A new target must be clearly better before the camera switches. This prevents jitter when multiple people satisfy the same command.

### Rate-Limited Pan/Tilt Control

The controller uses a deadband and per-step limit. The deadband prevents chatter near the image center; the step limit prevents unrealistic jumps.

## Extension Points

- Add command vocabulary in `command_parser.py`.
- Add ranking behavior or tune weights in `target_selector.py`.
- Tune pan/tilt response in `pan_tilt_controller.py`.
- Improve camera detections or color attributes in `vision.py`.
- Add speech or VLM input handling in `runtime_inputs.py`.
- Add new Gazebo people or props in `Simulation/generate_room_427_furnishings.py`.
- Add tests before changing selection or control behavior.
