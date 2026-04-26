Subject: IE 582 Final Project Progress Report

Hello Professor,

Here is the link to my final project repository:

https://github.com/akadam3-UB/IE582-Final_Project

I added my current status report to the README in the repo.

Since the original proposal, I narrowed the project scope to a speech-guided **pan/tilt camera tracking** system. The current plan is to use local speech-to-text for the spoken command, a local language model for command parsing, `Ultralytics + tracking` for the fast real-time loop, and a slower vision-language model such as `Qwen-VL` only when I need to disambiguate requests like `"the person in the red shirt"`. For simulation, I plan to build on the class-wide Gazebo model of the lab environment that we are creating together.

Most of my progress so far has been in refining the scope, studying the class pan/tilt interface, choosing the software architecture, incorporating the shared Gazebo environment plan, and building the initial scaffold in the repo for command parsing, target prioritization, and pan/tilt control output. I am still working toward full live integration with the class pan/tilt interface and the speech components.

One area where I would appreciate guidance is model selection for the slower grounding step. If you have a recommendation between options like `Qwen-VL` and `Moondream` for a lightweight local setup, that would help. I also want to confirm expectations for using the shared class Gazebo lab model as part of the development and evaluation process for the final demo.

Best,
Abhijeet Kadam
