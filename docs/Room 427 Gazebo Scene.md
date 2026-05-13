# Room 427 Gazebo Scene

## Purpose

The Room 427 scene is the project-local simulation environment for the text- or speech-guided pan/tilt tracking demo. It combines the measured classroom shell with a generated classroom/lab layer so target-selection commands can be tested in a realistic, repeatable scene.

## Main Files

- [Simulation/worlds/room_427.world](../Simulation/worlds/room_427.world): detailed room without the pan/tilt camera.
- [Simulation/worlds/room_427_tracking_test.world](../Simulation/worlds/room_427_tracking_test.world): detailed room plus the `pantilt` camera model.
- [Simulation/generate_room_427_furnishings.py](../Simulation/generate_room_427_furnishings.py): generator for the furniture and local people proxy models.
- [Simulation/Models/room_427_furnishings/model.sdf](../Simulation/Models/room_427_furnishings/model.sdf): generated furniture, yellow tape, tile seams, blinds, cabinets, AprilTag-style board, rack, workcell props, totes, and boxes.
- [Simulation/Models/person_proxy_red/model.sdf](../Simulation/Models/person_proxy_red/model.sdf): local red-shirt person proxy. Matching blue, green, and yellow models live beside it.

## Tracking Demo

Launch the Room 427 tracking world:

```bash
./scripts/run_gazebo_room_427_tracking_world.sh
```

In another terminal, run the pose-based fallback tracker:

```bash
echo "track the red person" > runtime_command.txt
./scripts/run_gazebo_room_427_pose_tracker.sh
```

Change the command while the tracker is running:

```bash
echo "track the blue person on the right" > runtime_command.txt
echo "track the green person in the center" > runtime_command.txt
echo "track the yellow person" > runtime_command.txt
```

The pose tracker reads color hints from Gazebo entity names such as `person_red_left`, which makes the demo stable even when Gazebo rendering is unstable on the local machine.

The current room intentionally omits the middle conveyor so the scene reads more like the photographed classroom/lab layout: tables, chairs, people, cabinets, racks, boxes, floor tape, and workcell props.

## Regenerating The Scene Models

After changing the generator, rebuild the generated model folders with:

```bash
python3 Simulation/generate_room_427_furnishings.py
xmllint --noout Simulation/Models/room_427_furnishings/model.sdf
```

The launch scripts set `GZ_SIM_RESOURCE_PATH` to `Simulation/Models`, so Gazebo can resolve `model://room_427_furnishings` and the local `person_proxy_*` models.
