# Asgard Usage Guide

Quick reference guide for using the enhanced Asgard robot control system.

## Table of Contents
1. [Getting Started](#getting-started)
2. [Programming Actions](#programming-actions)
3. [Computer Vision](#computer-vision)
4. [Vision-Guided Control](#vision-guided-control)
5. [Tips and Best Practices](#tips-and-best-practices)

---

## Getting Started

### Basic Connection

```python
from robot_controller import RobotController

robot = RobotController()

# Linux/Mac
robot.connect('/dev/ttyUSB0', baudrate=115200)

# Windows
# robot.connect('COM3', baudrate=115200)

# Always home first
robot.send_homing_command()
```

### Simple Movements

```python
from robot_controller import MovementType

# Rapid movement (G0) - fastest
robot.move_joint('A', 45.0, MovementType.G0_RAPID)

# Linear movement (G1) - controlled speed
robot.move_joint('A', 45.0, MovementType.G1_LINEAR, feedrate=300)

# Move multiple joints at once
robot.move_all_joints(
    {'A': 0, 'B': 30, 'D': -20},
    MovementType.G1_LINEAR,
    feedrate=400
)
```

### Joint Reference

| Joint ID | Name | Range | Description |
|----------|------|-------|-------------|
| A | Art1 | -180° to 180° | Base rotation |
| B | Art2 | -90° to 90° | Shoulder |
| C | Art3 | -90° to 90° | Linked to Art2 |
| D | Art4 | -90° to 90° | Elbow |
| X | Art5 | -90° to 90° | Wrist pitch |
| Y | Art6 | -90° to 90° | Wrist roll |
| Z | - | -180° to 180° | Gripper rotation |

---

## Programming Actions

### Recording Sequences

```python
from action_sequencer import ActionSequencer

sequencer = ActionSequencer(robot)

# Start recording
sequencer.start_recording("Pick and Place v1")

# All movements during recording will be captured
sequencer.record_move_joint('A', 45.0, MovementType.G1_LINEAR, feedrate=300)
sequencer.record_move_joint('B', 30.0, MovementType.G1_LINEAR, feedrate=300)
sequencer.record_gripper(100)  # Open
sequencer.record_wait(0.5)     # Wait 500ms
sequencer.record_gripper(0)    # Close

# Stop recording
sequencer.stop_recording()

# Save for later use
sequencer.save_sequence('my_sequence.json')
```

### Playing Back Sequences

```python
# Load a saved sequence
sequencer.load_sequence('my_sequence.json')

# Play with original timing
sequencer.play_sequence(respect_timing=True)

# Or play as fast as possible
sequencer.play_sequence(respect_timing=False)

# Stop playback if needed
sequencer.stop_playback()
```

### Pre-defined Sequences

```python
from action_sequencer import create_pick_and_place_sequence

# Define positions (joint angles)
pick_pos = {'A': 45, 'B': 30, 'D': -20, 'X': 10}
place_pos = {'A': -45, 'B': 30, 'D': -20, 'X': 10}

# Create the sequence
sequence = create_pick_and_place_sequence(
    pick_position=pick_pos,
    place_position=place_pos,
    approach_height=10.0,  # Safety offset in degrees
    name="Auto Pick-Place"
)

# Execute it
sequencer.play_sequence(sequence)
```

### Creating Custom Sequences Programmatically

```python
from action_sequencer import ActionSequence, Action, ActionType

sequence = ActionSequence("Custom Routine")

# Add actions manually
sequence.add_action(Action(
    ActionType.MOVE_ALL,
    parameters={
        'positions': {'A': 0, 'B': 0, 'D': 0},
        'movement_type': 'G1',
        'feedrate': 300
    },
    description="Go to home position"
))

sequence.add_action(Action(
    ActionType.WAIT,
    parameters={'duration': 1.0},
    description="Wait 1 second"
))

# Save and play
sequence.save_to_file('custom.json')
sequencer.play_sequence(sequence)
```

---

## Computer Vision

### Basic Object Detection

```python
from vision_controller import VisionController, DetectionMethod

vision = VisionController(camera_index=0)
vision.start_camera()

# Choose detection method
vision.detection_method = DetectionMethod.CONTOUR_DETECTION

# Process a frame
frame, objects = vision.process_frame()

print(f"Found {len(objects)} objects")
for obj in objects:
    print(f"  - Object at ({obj.center_x}, {obj.center_y})")
    print(f"    Size: {obj.width}x{obj.height}")
    print(f"    Confidence: {obj.confidence:.2f}")
```

### Detection Methods

#### 1. Contour Detection (General Purpose)
```python
vision.detection_method = DetectionMethod.CONTOUR_DETECTION
frame, objects = vision.process_frame()
```

#### 2. Color-Based Detection
```python
import numpy as np

vision.detection_method = DetectionMethod.COLOR_THRESHOLD

# Set HSV color range (example: red objects)
vision.color_lower = np.array([0, 100, 100])
vision.color_upper = np.array([10, 255, 255])

frame, objects = vision.process_frame()
```

#### 3. ArUco Marker Detection
```python
vision.detection_method = DetectionMethod.ARUCO_MARKER
frame, objects = vision.process_frame()

for obj in objects:
    print(f"Detected marker: {obj.label}")
```

### Live Display

```python
import cv2

while True:
    frame, objects = vision.process_frame()

    if frame is not None:
        cv2.imshow('Detection', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
vision.stop_camera()
```

---

## Vision-Guided Control

### Camera Calibration

Before using vision to guide the robot, you must calibrate the camera-to-robot coordinate transformation.

```python
# Step 1: Place markers at known robot positions
# Step 2: Record pixel coordinates and robot coordinates

camera_points = [
    (120, 90),   # Top-left marker in pixels
    (520, 90),   # Top-right marker
    (120, 390),  # Bottom-left marker
    (520, 390)   # Bottom-right marker
]

robot_points = [
    (-200, -200, 0),  # Top-left in robot coords (x, y, z in mm)
    (200, -200, 0),   # Top-right
    (-200, 200, 0),   # Bottom-left
    (200, 200, 0)     # Bottom-right
]

# Step 3: Calibrate
vision.transformer.calibrate_from_points(camera_points, robot_points)

# Step 4: Save calibration for later
vision.transformer.save_calibration('camera_calibration.npz')
```

### Using Calibration

```python
# Load saved calibration
vision.transformer.load_calibration('camera_calibration.npz')

# Detect object
frame, objects = vision.process_frame()

if objects:
    # Convert pixel coordinates to robot coordinates
    obj = objects[0]
    robot_coords = vision.get_robot_coordinates(obj)

    if robot_coords:
        x, y, z = robot_coords
        print(f"Object is at robot position: X={x:.1f}, Y={y:.1f}, Z={z:.1f} mm")

        # Now you can use these coordinates with inverse kinematics
        # to move the robot to the object
```

### Complete Vision-Guided Example

```python
from robot_controller import RobotController
from vision_controller import VisionController, DetectionMethod
from action_sequencer import ActionSequencer

# Setup
robot = RobotController()
vision = VisionController(camera_index=0)
sequencer = ActionSequencer(robot)

robot.connect('/dev/ttyUSB0')
vision.start_camera()

# Load calibration
vision.transformer.load_calibration('camera_calibration.npz')

# Set detection method
vision.detection_method = DetectionMethod.ARUCO_MARKER

# Detection loop
while True:
    frame, objects = vision.process_frame()

    # If marker detected, trigger action
    if objects:
        marker = objects[0]
        print(f"Detected {marker.label}")

        # Get robot coordinates
        coords = vision.get_robot_coordinates(marker)
        if coords:
            x, y, z = coords
            print(f"Target position: {x:.1f}, {y:.1f}, {z:.1f}")

            # Here you would:
            # 1. Calculate inverse kinematics to reach (x, y, z)
            # 2. Execute movement
            # 3. Perform pick/place action

        break

vision.stop_camera()
robot.disconnect()
```

---

## Tips and Best Practices

### Safety

1. **Always home first**: Call `robot.send_homing_command()` after connecting
2. **Check limits**: The `RobotController` automatically validates angle limits
3. **Emergency stop**: Keep your hand near the power button
4. **Test slowly**: Use lower feedrates (200-300) when testing new sequences

### Performance

1. **Feedrate guidelines**:
   - Fast movements: 500-1000 deg/min
   - Normal movements: 300-500 deg/min
   - Precise movements: 100-300 deg/min

2. **Vision processing**:
   - Reduce camera resolution for faster processing
   - Use simpler detection methods when possible
   - Process every 2nd or 3rd frame if real-time not needed

### Debugging

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check robot connection
if robot.is_connected():
    print("Robot connected")
else:
    print("Robot not connected")

# Get current position
pos = robot.get_current_position()
print(f"Current position: {pos}")

# Get current state
state = robot.get_state()
print(f"Robot state: {state}")
```

### Common Issues

**Robot not responding:**
- Check serial port connection
- Verify baud rate (should be 115200)
- Try unplugging and reconnecting USB
- Check if another program is using the port

**Vision detection not working:**
- Check camera index (try 0, 1, 2)
- Verify camera permissions
- Adjust detection thresholds
- Ensure good lighting conditions

**Sequence not playing:**
- Check robot connection
- Verify sequence file exists and is valid JSON
- Ensure robot is not in alarm state (use `send_kill_alarm()`)

---

## Common Workflows

### Workflow 1: Manual Teach and Repeat

```python
# 1. Record your manual movements
sequencer.start_recording("Task 1")

# 2. Manually move robot using GUI or code
robot.move_joint('A', 45, MovementType.G1_LINEAR, feedrate=300)
sequencer.record_move_joint('A', 45, MovementType.G1_LINEAR, feedrate=300)
# ... more movements ...

# 3. Stop and save
sequencer.stop_recording()
sequencer.save_sequence('task1.json')

# 4. Repeat automatically
sequencer.load_sequence('task1.json')
for i in range(10):  # Repeat 10 times
    sequencer.play_sequence(respect_timing=True)
    time.sleep(2)  # Wait between iterations
```

### Workflow 2: Vision-Based Sorting

```python
# 1. Calibrate camera
vision.transformer.calibrate_from_points(cam_pts, robot_pts)

# 2. Define sort positions
bin_a = {'A': 45, 'B': 30, 'D': -20}
bin_b = {'A': -45, 'B': 30, 'D': -20}

# 3. Detection and sorting loop
while True:
    frame, objects = vision.process_frame()

    for obj in objects:
        # Determine which bin based on color/size/etc
        target_bin = bin_a if obj.width > 100 else bin_b

        # Create and execute pick-place
        pick_coords = vision.get_robot_coordinates(obj)
        # ... calculate IK and execute ...
```

### Workflow 3: Automated Assembly

```python
# Load pre-recorded assembly steps
step1 = ActionSequence.load_from_file('pick_part.json')
step2 = ActionSequence.load_from_file('place_part.json')
step3 = ActionSequence.load_from_file('press_part.json')

# Execute assembly
for i in range(5):  # Build 5 assemblies
    print(f"Building assembly {i+1}")
    sequencer.play_sequence(step1)
    sequencer.play_sequence(step2)
    sequencer.play_sequence(step3)
    print(f"Assembly {i+1} complete")
```

---

## Additional Resources

- Full examples: Run `python examples.py`
- API documentation: See docstrings in each module
- Community: [Thor Robot Google Group](https://groups.google.com/forum/#!forum/thor-opensource-3d-printable-robotic-arm)
- Issues: Report bugs on GitHub

---

**Happy robot programming!** 🤖
