# Speech-Guided Pan/Tilt Target Tracking System

Team Members:
- Abhijeet Kadam, akadam3@buffalo.edu

---

## Project Objective

Develop a speech-guided multi-target tracking system for a **pan/tilt camera platform**. When multiple objects or people appear in the camera feed, the system will accept a spoken request, identify the intended target, and keep the selected target centered in view.

The updated concept is:

1. A user gives a spoken command such as `"track the person in the red shirt"`.
2. A local speech-to-text model such as `Whisper` converts speech to text.
3. A lightweight local language model converts the text into a structured command.
4. A real-time vision stack using `Ultralytics` and persistent tracking IDs selects candidate targets.
5. A slower vision-language model such as `Qwen-VL` can be used when attribute grounding is needed for descriptions like clothing color.
6. The class-wide Gazebo model of the lab will be used as the shared simulation environment for testing and development.
7. The pan/tilt controller moves the camera to keep the selected target centered.

## Contributions

This project adds a decision-making layer on top of standard object tracking. Instead of simply following the most obvious object, the system attempts to interpret user intent and resolve ambiguity when multiple valid targets are present. The project also combines human-robot interaction with real-time camera control by linking speech, command parsing, object tracking, and pan/tilt actuation in a single pipeline.

## Project Plan

The project will be organized into four stages:

1. **Pan/tilt tracking loop**
   - Build the image-space to pan/tilt control loop
   - Confirm the camera can stay centered on a selected tracked target
2. **Multi-target prioritization**
   - Detect and track multiple objects with persistent IDs
   - Rank candidates based on center proximity, size, confidence, and class priority
3. **Speech-command interface**
   - Use local speech-to-text to convert spoken requests into text
   - Use a local LLM to convert the text into a structured target request
4. **Attribute-level grounding**
   - Use a slower VLM only when needed for requests such as `"the guy in a red shirt"`
   - Keep the VLM out of the real-time loop and use it only for disambiguation

The project will use the shared class Gazebo model of the lab as the main simulation environment before or alongside physical robot testing.

Development will use Python together with OpenCV, `Ultralytics`, local speech-recognition tools, and a pan/tilt control interface from the course codebase. Reference material will include course resources and standard computer vision literature.

## Milestones / Schedule Checklist

- [x] Complete this proposal document.  *Due March 31*
- [x] Refine project scope toward a pan/tilt camera system.
- [x] Create progress report / status report in repo.  *Due April 21*
- [x] Create initial command parsing, target ranking, and pan/tilt control scaffold.
- [ ] Integrate live multi-object tracking with persistent target IDs.
- [ ] Implement live pan/tilt target locking on the class robot interface.
- [ ] Add speech-to-text input and local LLM command parsing.
- [ ] Add VLM-based grounding for difficult appearance-based commands.
- [ ] Integrate and test inside the shared class Gazebo lab model.
- [ ] Test and validate on real scenes.
- [ ] Create final presentation.  *Due May 5*
- [ ] Finalize system documents.
- [ ] Provide final system documentation / README.  *Due May 15*

## Measures of Success

- [ ] Vision model detects multiple objects in the scene.
- [ ] System assigns a priority score to candidate targets.
- [ ] Correct target is selected from a spoken request.
- [ ] Pan/tilt camera remains locked on the selected target during motion.
- [ ] Speech input is correctly converted into a usable target command.
- [ ] VLM grounding improves performance for appearance-based requests.
- [ ] User can run the system end-to-end on the class pan/tilt setup.

## Updates After Meeting

- Narrow scope to **pan/tilt camera**, not robotic car.
- Use `Whisper` or similar local STT for spoken commands.
- Use a local LLM for command parsing.
- Use `Ultralytics + ByteTrack` style tracking for the fast loop.
- Use `Qwen-VL` or a similar model only as a slower grounding helper.
- Use the class-wide Gazebo lab model as the shared simulation environment.
