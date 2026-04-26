# Evaluation Plan

## 1. Evaluation Objective

The final system should be judged on more than whether the camera moves. The meaningful evaluation question is:

**Does the system select the correct target from a human command and keep that target stably centered over time?**

This breaks into two subproblems:

1. intent resolution
2. visual tracking and camera control

## 2. Main Metrics

### 2.1 Target Selection Accuracy

For each command, record whether the chosen target matches the intended person or object.

Metric:

- `selection_accuracy = correct selections / total commands`

### 2.2 Lock Retention

Measure how often the camera stays on the chosen target after selection.

Possible metric:

- fraction of frames where the selected target remains within a center tolerance band

### 2.3 Reacquisition Time

If the target leaves the center or is briefly lost, record how long it takes to recover.

Metric:

- time or number of frames to re-center

### 2.4 False Switch Count

Count how often the system switches to another target without a new command.

This is especially important in multi-person scenes. A system that moves but frequently jumps to the wrong person is not successful.

### 2.5 Command-to-Action Latency

Measure how long it takes from the spoken command to the first correct tracking response.

This helps separate STT/grounding delay from tracking delay.

## 3. Test Scenario Matrix

The evaluation should cover progressively harder scenes.

### Scenario A: Single Target

Examples:

1. `track the person`
2. `track the cone`

Purpose:

- verify the basic detection, selection, and control loop

### Scenario B: Multiple Same-Class Targets

Examples:

1. two or more people in frame
2. two or more cones in frame

Purpose:

- verify that the system can maintain target identity instead of switching arbitrarily

### Scenario C: Attribute-Based Commands

Examples:

1. `track the red cone`
2. `track the person on the left`

Purpose:

- validate lightweight grounding from color and spatial hints

### Scenario D: Ambiguous Commands

Examples:

1. `track the person`
2. `track the student`

Purpose:

- observe whether the system stays stable even when the command is underspecified

### Scenario E: Hard Grounding Commands

Examples:

1. `track the person in the red shirt`
2. `track the person near the board`

Purpose:

- evaluate the added value of the slow VLM path

## 4. Ablation Plan

To make the final evaluation more convincing, compare a few reduced versions of the system.

### Ablation 1: No Sticky/Hysteresis Logic

Question:

- does target switching increase without stability logic?

Expected result:

- more false switches in multi-target scenes

### Ablation 2: No Color/Region Cues

Question:

- how much do lightweight attributes help before using a VLM?

Expected result:

- worse performance on `red` / `left` style commands

### Ablation 3: No VLM Grounding

Question:

- which command types are already handled by fast logic, and which truly require slower reasoning?

Expected result:

- simple commands stay strong, harder relational commands degrade

## 5. Simulation vs Hardware

Evaluation should be split into two environments.

### 5.1 Gazebo Classroom World

Use Gazebo for:

1. repeatable target layouts
2. multi-object scenarios
3. debugging before hardware time

Advantages:

1. easier iteration
2. repeatability
3. safer testing of pipeline logic

### 5.2 Physical Pan/Tilt Platform

Use the real system for:

1. camera motion realism
2. lighting variation
3. real-world speech and visual noise

Advantages:

1. validates assumptions from simulation
2. shows whether the project is robust outside idealized conditions

## 6. Minimum Viable Final Demo

A good final demo does not need to solve every grounding problem. A strong MVP would show:

1. spoken command captured locally
2. command parsed into structured intent
3. multiple targets visible
4. correct target selected
5. pan/tilt camera keeps the target centered

Suggested demo commands:

1. `track the person`
2. `track the person on the left`
3. `track the red cone`
4. `stop`

## 7. Stretch Goal Demo

If time permits, add one richer command that uses the slow grounding path, such as:

1. `track the person in the red shirt`

This should be treated as a stretch goal because it adds appearance and relation ambiguity beyond the current lightweight attributes.

## 8. Evidence To Save In Repo

To make the final submission stronger, save:

1. short video clips or screenshots
2. example commands used
3. selected target IDs
4. basic metric summaries
5. notes on failure cases

Even a small table of results is better than only narrative claims.

## 9. Final Evaluation Thesis

The final evaluation should demonstrate that the project is successful not when the camera merely moves, but when:

1. the intended target is chosen correctly
2. the camera motion remains stable
3. the system resists unnecessary target switching
4. the design scales from simple commands to harder grounding tasks
