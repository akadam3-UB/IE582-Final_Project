# Multi-Target Prioritization System

Team Members:
- Abhijeet Kadam, akadam3@buffalo.edu

--- 

## Project Objective
Develop a multi-target prioritization and tracking system for a robotic platform such as a pan/tilt camera or robotic car. When multiple objects are present in the camera feed, the system will select a single target using a defined prioritization strategy based on factors such as distance from the image center, object size, detection confidence, and class priority. Once selected, the robot will track the target in real time.
As an extenstion the system will also support voice based target selection command. The voice command could be 'Target the person in
red shirt' and the camera will identify person in red shirt based on AI model and track the specific target in a scene with multiple objects.

## Contributions
This system will add prioratization layer that evaluates all detections and selects the most relevent target within multiple object detections within scene, adding onto the current tracking logic which is effective for single target, but does not address decision-making problem arised due to multiple valid targets appearing in scene. This will also be extended to human-robot interaction by allowing voice to set target.

## Project Plan
The project will integrate a computer vision detecton and tracking pipeline with control system of robotic platform. The first phase will focus on detecting multiple objects, maintaining persistent identities across frames, and computing a target priority score using rule-based logic. The selected target will then be passed to the tracking controller for camera or vehicle motion.
A secondary phase will add voice-command functionality so that a user can specify the desired target by class or visible attribute.
Development will use Python together with OpenCV, Ultralytics-based object detection/tracking tools, and speech-recognition modules. Reference material will include course resources and standard computer vision literature such as *Computer Vision: Algorithms and Applications*.

## Milestones/Schedule Checklist
- [x] Complete this proposal document.  *Due March 31*
- [ ] Integrate multi-object detection and persistent target IDs.
- [ ] Implement prioritization logic based on center proximity, bounding-box size, confidence, and class priority.
- [ ] Create progress report.  *Due April 21*
- [ ] Extend the tracking logic to the robotic car platform.
- [ ] Implement voice-command target selection as an extension feature.
- [ ] Test and validate.
- [ ] Create final presentation.  *Due May 5*
- [ ] Finalize system documents.
- [ ] Provide system documentation (README.md).  *Due May 15*


## Measures of Success
- [ ] Vision model detects multiple objects in scene.
- [ ] System assigns a priority score to each detected target.
- [ ] Correct target is selected based on prioratization rule.
- [ ] Pan/tilt camera remains locked on selected target during motion.
- [ ] The robotic car moves toward or follows the selected target.
- [ ] Voice command correctly selects intended target when enabled.
- [ ] User can correctly run system to perform intended target tracking/following.


## Updates to Proposal

- Understand scene utilizing Vision Language models
- Natural speech processing using local language model
- Collaborate with student within class for scene setup