# Technical Design

## 1. Problem Framing

The project goal is not simply to make a pan/tilt camera move. The real problem is:

1. observe a scene with multiple possible targets
2. interpret a human command about which target matters
3. choose the intended target robustly
4. keep that target centered without unstable camera motion

That framing matters because it drives the architecture. A plain tracker solves only step 4. This project adds the decision layer between language and motion.

## 2. Why Pan/Tilt Instead of a Car

The earlier project direction could have expanded into a mobile robot or car. That path was intentionally narrowed to a pan/tilt camera for three reasons:

1. The core research question here is **language-guided target selection**, not navigation.
2. A car adds localization, obstacle avoidance, path planning, and safety concerns that would dominate the semester.
3. The class already has a pan/tilt platform and prior ArUco-tracking experience, so this project can build on known hardware and known control interfaces.

This makes the project more coherent. The system is now a **smart classroom camera** rather than a partially finished mobile robot.

## 3. System Architecture

The design is split into a fast loop and a slow loop.

### 3.1 Fast Loop

Runs every frame or near frame rate:

1. camera frame acquisition
2. object detection + tracking with persistent IDs
3. lightweight visual attributes from the tracked crop
4. target scoring and selection
5. pan/tilt command generation

This loop must stay lightweight because it directly determines tracking stability.

### 3.2 Slow Loop

Runs only when needed:

1. speech transcription
2. command parsing into a structured intent
3. optional VLM grounding for ambiguous descriptions

This loop can be slower because it updates intent, not motor commands on every frame.

### 3.3 Design Principle

The key architectural principle is:

**Use heavy models for interpretation, but keep actuation decisions on lightweight, bounded logic.**

That is why `Qwen-VL` or another VLM is treated as an optional helper rather than the main real-time controller.

## 4. Core Data Flow

The implemented pipeline currently follows this shape:

1. `Whisper` or `mlx-whisper` converts speech to text
2. `command_parser.py` converts text into a `CommandIntent`
3. `Ultralytics` tracking produces labeled detections with track IDs
4. `vision.py` converts detections into project models and estimates simple attributes such as dominant color
5. `target_selector.py` ranks candidates
6. `pan_tilt_pipeline.py` applies stability rules and chooses the target to follow
7. `pan_tilt_controller.py` converts image error into joint commands
8. transport scripts publish commands to Gazebo or the class socket host

## 5. Target Selection Reasoning

The target selector combines several signals:

1. center proximity
2. apparent size
3. detector confidence
4. class priority
5. command matches such as label, color, region, or explicit track ID

This is intentionally a weighted heuristic instead of a learned policy. The reasons are:

1. the class environment does not provide enough data to train a stable learned policy
2. debugging matters more than squeezing out a few points of performance
3. the selector needs to be interpretable for demos and reporting

Each selected target can be explained by its score breakdown, which is useful for analysis and failure diagnosis.

## 6. Stability and Control Reasoning

Two stability problems matter in a multi-target pan/tilt system:

1. **selection instability**: bouncing between similar objects
2. **control instability**: large, jerky camera corrections

### 6.1 Selection Stability

The current implementation now uses two stabilizers:

1. **sticky target preference**
   - if the current track is still a strong candidate, prefer it
2. **switch margin hysteresis**
   - do not switch to a new target unless it is clearly better than the current one

This matters because in a classroom scene, multiple people may all satisfy a command like `"track the person"`. Without hysteresis, the camera can alternate between them frame to frame.

### 6.2 Control Stability

The controller uses:

1. deadbands in pixels
2. image-space error mapped to angular corrections
3. joint limit clamping
4. max per-step angular rate limiting

The deadband avoids chatter near the image center. The per-step cap avoids unrealistic or unstable jumps when the target is far from center.

## 7. Fast Attributes vs Slow Grounding

The repo currently supports simple attribute grounding directly from the image crop:

1. dominant color
2. left/center/right region

These are cheap and useful for commands like:

1. `track the red cone`
2. `track the professor on the left`

However, these lightweight attributes are not enough for richer requests like:

1. `track the student in the red shirt near the board`
2. `track the person next to the door`

Those commands require either:

1. better scene semantics
2. relational reasoning
3. a slower VLM grounding pass

That is why the project still needs a slow-grounding stage even though the fast loop already has some attribute reasoning.

## 8. Current Implementation Maturity

The repo now has meaningful structure in four areas:

1. command understanding
2. target ranking
3. control output
4. execution scripts for Gazebo, host sockets, and macOS speech input

It is no longer just a proposal repo. But it is also not yet an end-to-end validated robot system. The current maturity level is best described as:

**implemented architecture + tested core logic + pending live integration**

That is an important distinction, and it keeps the repo honest.

## 9. Known Limitations

The most important limitations are:

1. no full live microphone-to-tracker demonstration has been validated yet
2. no classroom-world Gazebo experiment results are stored yet
3. no physical pan/tilt robot experiment results are stored yet
4. color estimation is intentionally simple and may fail under poor lighting
5. VLM grounding is architected but not fully integrated into the main runtime path

## 10. Engineering Priorities From Here

The next steps should be driven by risk reduction, not by adding more code at random.

### Priority 1: End-to-End Intent Updates

Prove that a spoken command can change the active tracking target during runtime.

### Priority 2: Live Tracker Integration

Run the pipeline continuously on the Gazebo classroom camera topic or physical camera stream.

### Priority 3: Store Results

Collect concrete runs showing:

1. command issued
2. chosen target
3. whether the choice was correct
4. whether the camera remained locked

### Priority 4: Harder Grounding

Only after the basic path is stable should the project spend time on slower VLM reasoning.

## 11. Final Design Thesis

The project should be understood as:

**an intent-driven smart camera that bridges human language and real-time visual servoing in a multi-target scene**

That is a stronger and more defensible thesis than simply calling it object tracking.
