# IE582 Final Project

## Status Report

**Date:** April 24, 2026  
**Student:** Abhijeet Kadam  
**Repo:** [akadam3-UB/IE582-Final_Project](https://github.com/akadam3-UB/IE582-Final_Project)

### Status Summary

The project direction is now clearly defined, but the work is still in the **early implementation and integration stage**. Most of the progress so far has been in narrowing the scope, analyzing the class pan/tilt interface, choosing the software architecture, and building the initial code scaffold rather than completing full live robot testing.

### Project Summary

The project is now focused on a **speech-guided pan/tilt camera tracking system**. The goal is for a user to give a spoken command such as `"track the person in a red shirt"` and have the system select the correct target from a multi-object scene and keep the pan/tilt camera centered on that target.

### Current Direction After Meeting

The architecture discussed in meeting is:

1. **Interface**
   - Speech-to-text using `Whisper` or similar local STT
   - A local `LLM` to turn the spoken request into a structured command
2. **Real-time tracking**
   - `Ultralytics` object detection with `ByteTrack`-style persistent IDs
   - This is the fast loop used every frame
3. **Grounding for harder descriptions**
   - A slower vision-language model such as `Qwen-VL` to help resolve requests like `"the guy in a red shirt"`
   - This model is intended to run only when needed, not on every frame
4. **Environment**
   - The project will use the class-wide Gazebo model of the lab as the shared simulation environment
5. **Control output**
   - The selected tracked target is converted into pan/tilt joint commands for the class robot interface

### Progress Completed

- Refined the project scope from a broader multi-target robotics idea into a more realistic **speech-guided pan/tilt camera tracking system**.
- Reviewed the class robot software stack and identified the relevant pan/tilt control path, especially the socket-based command interface used by the course demos.
- Aligned the project plan with the class effort to build a shared Gazebo model of the lab environment for simulation and testing.
- Chose the working architecture discussed in meeting:
  - local speech-to-text for spoken commands
  - local LLM for structured command parsing
  - `Ultralytics + persistent tracking IDs` for the fast loop
  - slower VLM grounding only when the request is ambiguous
- Built an initial Python scaffold for:
  - command parsing
  - target ranking and prioritization
  - pan/tilt control output
  - host-socket payload formatting for the class pan/tilt system
- Extended the scaffold so detections can now carry simple appearance attributes from the image itself, especially dominant color for commands such as `"track the red cone"` or `"track the person on the left"`.
- Added a demo pan/tilt pipeline and a socket client script aligned with the class `socket_demo` control flow.
- Added unit tests covering parsing, ranking, pan/tilt command generation, and pipeline behavior.
- Updated the repo documentation and proposal so the written project plan now matches the current technical direction.

### Work Completed Since The Last Meeting

The work completed since the meeting has been mostly preparation and initial implementation:

1. Clarified the system architecture and reduced scope to the pan/tilt camera setup.
2. Studied the class repo to identify how pan/tilt status and command messages are sent.
3. Defined the division between the fast real-time tracker and the slower grounding model.
4. Incorporated the shared class Gazebo lab-model effort into the project plan as the intended simulation environment.
5. Created a first-pass software structure for command parsing, target selection, and control output.
6. Added local demos and tests so the core logic can be iterated on before full robot integration.

### Current Repo State

The repo currently contains the following key components:

- [src/ie582_final_project/command_parser.py](src/ie582_final_project/command_parser.py)
  - rule-based command parsing with optional VLM JSON override
- [src/ie582_final_project/target_selector.py](src/ie582_final_project/target_selector.py)
  - target scoring based on center proximity, size, confidence, class priority, command match, and sticky track preference
- [src/ie582_final_project/pan_tilt_controller.py](src/ie582_final_project/pan_tilt_controller.py)
  - image error to pan/tilt joint command conversion
- [src/ie582_final_project/pan_tilt_pipeline.py](src/ie582_final_project/pan_tilt_pipeline.py)
  - end-to-end selection and control loop with target lock across frames
- [src/ie582_final_project/vision.py](src/ie582_final_project/vision.py)
  - converts tracker outputs into project detections and estimates simple attributes like dominant color
- [scripts/pan_tilt_socket_client.py](scripts/pan_tilt_socket_client.py)
  - class-host integration script for `sessionstart`, `status`, and `command`
- [scripts/pan_tilt_gazebo_tracker.py](scripts/pan_tilt_gazebo_tracker.py)
  - Gazebo camera topic to pan/tilt tracking loop for the shared classroom world
- [scripts/mic_command_listener.py](scripts/mic_command_listener.py)
  - macOS microphone bridge that records short clips with `ffmpeg` and writes transcribed commands to a command file

### What Is Working Now

- Command text can be converted into a target-selection intent.
- Commands can now include simple spatial hints such as `left`, `right`, or `center`.
- Multiple detections can be ranked and the best target can be selected.
- The selector now keeps preference for the current tracked ID so the camera is less likely to bounce between similar targets.
- Simple color grounding now works directly from the camera image for detections, which supports commands such as `"track the red cone"` without needing a VLM on every frame.
- Pan/tilt output can be generated in the same command format used by the class pan/tilt socket interface.
- The class pan/tilt socket client can now update commands while running from a text file, audio file, or optional VLM JSON file.
- A Mac-friendly microphone listener path now exists so spoken commands can update `runtime_command.txt` live on a MacBook Air M2.
- A Gazebo pan/tilt tracker script now exists for the shared classroom world using the simulated pan/tilt camera topic.
- Local demo and automated tests run successfully in the repo.

### What Is Not Working Yet

- Live speech input is not yet wired into the tracking loop.
- The pan/tilt pipeline is not yet fully validated on robot.
- Rich grounding for requests like `"person in the red shirt near the board"` still needs a slower model or custom logic beyond the current basic color estimate.
- No quantitative robot experiments or final demo results have been collected yet.
- The Gazebo environment integration is dependent on the shared class lab model being ready enough for project-specific testing.

### What Still Needs To Be Done

- Connect the pipeline to live speech input.
- Replace the placeholder command parsing path with the final `Whisper + local LLM` interface.
- Integrate live `Ultralytics + tracking` results on the real robot stream.
- Add the slower VLM grounding path for harder appearance-based requests like clothing color, relative object references, or scene-specific descriptions.
- Connect the project logic to the shared Gazebo lab model for simulation-based testing.
- Test on the physical pan/tilt robot in a realistic environment with multiple people/objects.

### Current Risks / Open Questions

- The main design tradeoff is how often to call the VLM. It should help with grounding, but it is too slow for the per-frame loop.
- I still need to choose the best local grounding model for this project setup, likely between `Qwen-VL` and `Moondream`.
- I need to confirm the timeline and readiness of the shared class Gazebo lab model so I can use it effectively for project testing.
- The main remaining risk is integration time: the core logic exists in scaffold form, but the physical robot and speech components still need to be connected and tested together.

### Next Steps

1. Integrate the pan/tilt pipeline into the class control code path.
2. Add speech input and structured command extraction.
3. Test tracking with multiple people and ambiguous descriptions.
4. Add VLM-based disambiguation only when the fast tracker cannot resolve the request.

## Quick Run Commands

```bash
python3 scripts/demo_pan_tilt_pipeline.py --command "track the blue person" --robot-id 1
python -m pytest
```

## End-To-End Run Paths

Class pan/tilt interface:

```bash
python3 scripts/pan_tilt_socket_client.py \
  --host-url "https://HOST_IP:8085" \
  --robot-id 1 \
  --command "track the person"
```

Gazebo classroom world:

```bash
python3 scripts/pan_tilt_gazebo_tracker.py \
  --topic "/world/default/model/pantilt/link/tilt_link/sensor/camera/image" \
  --gazebo-model-name pantilt \
  --command "track the person"
```

Dynamic command updates while the system is running:

```bash
python3 scripts/pan_tilt_gazebo_tracker.py \
  --command-file runtime_command.txt \
  --vlm-json-file runtime_vlm.json
```

If `runtime_command.txt` changes, the active command is updated. If `runtime_vlm.json` changes, the parser will merge the VLM grounding output into the active intent. An audio file path can also be supplied with `--audio-file` if a local Whisper installation is available.

## MacBook Air M2 Speech Path

Recommended setup for Apple Silicon:

1. Use `mlx-whisper` as the speech backend when possible.
2. Use `ffmpeg` with macOS `avfoundation` to capture microphone snippets.
3. Feed the resulting transcribed command text into `runtime_command.txt`.

List available microphone devices:

```bash
python3 scripts/mic_command_listener.py --list-devices
```

Run the microphone listener in one terminal:

```bash
.venv/bin/python scripts/mic_command_listener.py \
  --output-command-file runtime_command.txt \
  --input-spec ":0" \
  --duration-sec 2.5 \
  --whisper-backend auto \
  --whisper-model base
```

Then run the tracker in another terminal:

```bash
.venv/bin/python scripts/pan_tilt_gazebo_tracker.py \
  --command-file runtime_command.txt \
  --whisper-backend auto \
  --whisper-model base
```

For the class host socket path instead of Gazebo:

```bash
.venv/bin/python scripts/pan_tilt_socket_client.py \
  --host-url "https://HOST_IP:8085" \
  --robot-id 1 \
  --command-file runtime_command.txt \
  --whisper-backend auto \
  --whisper-model base
```

If `mlx-whisper` is installed, the code will prefer it automatically on Apple Silicon. If not, it will fall back to the regular `whisper` package.
