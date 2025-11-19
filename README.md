# Asgard - Enhanced Robot Control System

Asgard is an enhanced Graphical User Interface (GUI) and control system for [Thor](https://github.com/AngelLM/Thor) - the open-source 6-axis robotic arm. Built with [PyQt5](https://riverbankcomputing.com/software/pyqt/download5) and now featuring advanced action programming and computer vision capabilities.

<img src="doc/AsgardGUI.png" width="800">

## Key Features

### Original Features
- **User-friendly Graphical Interface** - Intuitive control panel for manual operation
- **Forward Kinematics** - Direct joint angle control for all 6 axes
- **Real-time Position Feedback** - Live display of robot state and joint positions
- **Serial Communication** - Robust GRBL-based command protocol
- **Multi-platform Support** - Works on Windows, Linux, and macOS

### New Enhanced Features (2024)
- **Modular Robot Controller** - Clean API for programmatic robot control
- **Action Sequencer** - Record, save, load, and playback action sequences
- **Computer Vision Integration** - OpenCV-based object detection and tracking
- **3D Visualization & Control** - Interactive 3D viewer with drag-to-position interface
- **Forward/Inverse Kinematics** - Complete kinematics solver with numerical IK
- **Path Planning** - Smooth trajectory generation with multiple interpolation methods
- **Coordinate Transformation** - Convert between camera and robot coordinate systems
- **Vision-Guided Control** - Trigger actions based on visual detection
- **Pre-defined Sequences** - Built-in pick-and-place and custom sequences
- **Comprehensive Examples** - Ready-to-use code for common tasks

### Planned Features
- **Analytical IK Solver** - Faster analytical inverse kinematics
- **Collision Detection** - Self-collision and workspace obstacle avoidance
- **Force Control** - Compliant motion and force feedback

## What's New in Version 2.1

🎉 **Major Enhancements for Robotics Developers!**

- 🤖 **Modular Python API** - Control your robot programmatically with clean, documented APIs
- 📹 **Computer Vision Integration** - Built-in OpenCV support for visual object detection
- 🎬 **Action Recorder** - Record, save, and replay robot movements
- 🎮 **3D Interactive Control** - NEW! Visualize and control robot in 3D space
- 🧮 **Kinematics Solver** - NEW! Forward and inverse kinematics with numerical solver
- 🗺️ **Path Planning** - Generate smooth, interpolated trajectories
- ⚙️ **Configuration System** - Centralized settings management
- 🚀 **Quick Start Wizard** - Interactive setup for new users
- 📷 **Calibration Tools** - Easy camera-to-robot coordinate calibration
- 📚 **Comprehensive Examples** - Multiple interactive examples to get you started

See [CHANGELOG.md](CHANGELOG.md) for complete details.

## Installation

### Prerequisites
- Python 3.6 or higher
- USB connection to Thor robotic arm
- (Optional) Webcam or camera for vision features

### Quick Install

```bash
# Clone the repository
git clone https://github.com/DruishPrince/Valhalla.git
cd Valhalla

# Install dependencies
pip install -r requirements.txt

# Run the quick-start wizard (recommended for first-time users)
python quickstart.py
```

### Manual Installation

```bash
pip install PyQt5 pyserial opencv-python opencv-contrib-python numpy
```

## Quick Start

### Using the GUI

```bash
python asgard.py
```

1. Select your serial port from the dropdown
2. Choose baud rate (default: 115200)
3. Click "Connect"
4. Use the Forward Kinematics controls to move individual joints
5. Use the console for custom G-code commands

### Programmatic Control

```python
from robot_controller import RobotController, MovementType

# Create and connect to robot
robot = RobotController()
robot.connect('/dev/ttyUSB0', baudrate=115200)

# Home the robot
robot.send_homing_command()

# Move a single joint
robot.move_joint('A', 45.0, MovementType.G1_LINEAR, feedrate=300)

# Move multiple joints
robot.move_all_joints(
    {'A': 0.0, 'B': 30.0, 'D': -20.0},
    MovementType.G1_LINEAR,
    feedrate=400
)

# Control gripper
robot.move_gripper(50)  # 50% open

robot.disconnect()
```

## Using New Features

### Recording Action Sequences

```python
from robot_controller import RobotController
from action_sequencer import ActionSequencer, MovementType

robot = RobotController()
robot.connect('/dev/ttyUSB0')

sequencer = ActionSequencer(robot)

# Start recording
sequencer.start_recording("My First Sequence")

# Perform movements (these will be recorded)
sequencer.record_move_joint('A', 45.0)
sequencer.record_gripper(100)
sequencer.record_wait(1.0)
sequencer.record_gripper(0)

# Stop and save
sequencer.stop_recording()
sequencer.save_sequence('my_sequence.json')

# Play it back later
sequencer.load_sequence('my_sequence.json')
sequencer.play_sequence()
```

### Computer Vision

```python
from vision_controller import VisionController, DetectionMethod

# Create vision controller
vision = VisionController(camera_index=0)
vision.start_camera()

# Set detection method
vision.detection_method = DetectionMethod.CONTOUR_DETECTION

# Process frames and detect objects
frame, objects = vision.process_frame()

for obj in objects:
    print(f"Object at ({obj.center_x}, {obj.center_y})")

    # Convert to robot coordinates (requires calibration)
    robot_coords = vision.get_robot_coordinates(obj)
    if robot_coords:
        x, y, z = robot_coords
        print(f"  Robot position: {x:.1f}, {y:.1f}, {z:.1f}")
```

### Vision-Guided Pick and Place

```python
from robot_controller import RobotController
from vision_controller import VisionController, DetectionMethod
from action_sequencer import create_pick_and_place_sequence, ActionSequencer

robot = RobotController()
vision = VisionController()

robot.connect('/dev/ttyUSB0')
vision.start_camera()

# Calibrate camera-to-robot transformation
camera_points = [(100, 100), (500, 100), (100, 400), (500, 400)]
robot_points = [(-200, -200, 0), (200, -200, 0), (-200, 200, 0), (200, 200, 0)]
vision.transformer.calibrate_from_points(camera_points, robot_points)

# Detect object
frame, objects = vision.process_frame()
if objects:
    # Get robot coordinates for detected object
    target = vision.get_robot_coordinates(objects[0])

    # Create and execute pick-and-place
    # (Note: You'd need inverse kinematics for real implementation)
    print(f"Object detected at robot coordinates: {target}")
```

## Examples

The `examples.py` file contains comprehensive examples:

```bash
python examples.py
```

Available examples:
1. **Basic Robot Control** - Simple joint movements and gripper control
2. **Recording and Playing Sequences** - Create reusable action sequences
3. **Pre-defined Pick-and-Place** - Use built-in sequence templates
4. **Computer Vision Detection** - Object detection with multiple methods
5. **Vision-Guided Control** - Use camera to guide robot movements
6. **Vision-Triggered Sequence** - Automatic actions based on detection

## Quick Reference

### Essential Commands

| Task | Command |
|------|---------|
| Run GUI | `python asgard.py` |
| **3D Interactive Control** | `python robot_3d_control.py` |
| **3D Viewer (standalone)** | `python viewer_3d.py` |
| **3D Examples** | `python example_3d_control.py` |
| Quick setup wizard | `python quickstart.py` |
| Interactive examples | `python examples.py` |
| Calibrate camera | `python calibrate_camera.py` |
| Test kinematics | `python kinematics.py` |
| Test configuration | `python config_manager.py` |
| Test path planning | `python path_planner.py` |

### File Structure

| File | Purpose |
|------|---------|
| `robot_controller.py` | Core robot control API |
| `action_sequencer.py` | Record/playback sequences |
| `vision_controller.py` | Computer vision integration |
| **`kinematics.py`** | **Forward/inverse kinematics solver** |
| **`viewer_3d.py`** | **Interactive 3D visualization** |
| **`robot_3d_control.py`** | **3D control application (PyQt5)** |
| `path_planner.py` | Smooth path generation |
| `config_manager.py` | Configuration management |
| `calibrate_camera.py` | Camera calibration tool |
| `quickstart.py` | Interactive setup wizard |
| `examples.py` | Example workflows |
| **`example_3d_control.py`** | **3D control examples** |
| `asgard.py` | Original PyQt5 GUI |

### Configuration Files

| File | Purpose |
|------|---------|
| `asgard_config.json` | Main configuration (auto-created) |
| `camera_calibration.npz` | Camera calibration data |
| `sequences/*.json` | Saved action sequences |

### Common Workflows

**1. First Time Setup:**
```bash
python quickstart.py
```

**2. Record a Task:**
```python
from robot_controller import RobotController
from action_sequencer import ActionSequencer

robot = RobotController()
robot.connect('/dev/ttyUSB0')

sequencer = ActionSequencer(robot)
sequencer.start_recording("my_task")
# ... perform movements ...
sequencer.stop_recording()
sequencer.save_sequence('my_task.json')
```

**3. 3D Visualization and Control:**
```python
from viewer_3d import create_interactive_viewer
from kinematics import Point3D

# Create 3D viewer with sliders
viewer = create_interactive_viewer(use_sliders=True)

# Set target position (inverse kinematics)
target = Point3D(200, 100, 200)  # X, Y, Z in mm
viewer.set_target(target)

# Display interactive viewer
viewer.show()
```

**4. Inverse Kinematics:**
```python
from kinematics import ThorKinematics, Point3D

kin = ThorKinematics()

# Target position in 3D space
target = Point3D(x=200, y=100, z=200)

# Solve for joint angles
if kin.is_reachable(target):
    angles = kin.inverse_kinematics(target)
    print(f"Solution: {angles}")
    # Send to robot...
```

**5. Vision-Based Automation:**
```python
from vision_controller import VisionController

vision = VisionController()
vision.start_camera()
vision.transformer.load_calibration('camera_calibration.npz')

frame, objects = vision.process_frame()
for obj in objects:
    coords = vision.get_robot_coordinates(obj)
    # Move robot to coords...
```

## Module Documentation

### robot_controller.py
- `RobotController` - Main robot control class
- `MovementType` - G0 (rapid) or G1 (linear with feedrate)
- `RobotState` - Enum for robot states (Idle, Run, Home, Alarm, etc.)

Key methods:
- `connect(port, baudrate)` - Connect to robot
- `move_joint(joint, angle, movement_type, feedrate)` - Move single joint
- `move_all_joints(positions, movement_type, feedrate)` - Move multiple joints
- `move_gripper(percentage)` - Control gripper (0-100%)
- `send_homing_command()` - Home the robot
- `validate_angle(joint, angle)` - Check angle limits

### action_sequencer.py
- `ActionSequencer` - Record and playback sequences
- `ActionSequence` - Container for action sequences
- `Action` - Individual action (move, wait, gripper, etc.)
- `ActionType` - Types of actions available

Key methods:
- `start_recording(name)` - Begin recording
- `record_move_joint/record_gripper/record_wait()` - Record actions
- `stop_recording()` - Stop recording
- `save_sequence(filepath)` - Save to JSON file
- `load_sequence(filepath)` - Load from file
- `play_sequence(sequence, respect_timing)` - Execute sequence

### vision_controller.py
- `VisionController` - Computer vision control
- `CoordinateTransformer` - Camera-to-robot coordinate conversion
- `DetectedObject` - Represents detected object
- `DetectionMethod` - Detection algorithms (color, contour, ArUco, etc.)

Key methods:
- `start_camera()` - Initialize camera
- `detect_objects_by_color/contour/aruco()` - Different detection methods
- `process_frame()` - Process frame and detect objects
- `get_robot_coordinates(obj)` - Convert pixel to robot coords
- `calibrate_from_points()` - Calibrate transformation

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    asgard.py (GUI)                      │
│                 PyQt5 User Interface                    │
└──────────────┬──────────────────────────────────────────┘
               │
       ┌───────┴────────┬────────────────┬────────────────┐
       │                │                │                │
┌──────▼──────┐  ┌──────▼──────┐  ┌─────▼─────┐  ┌──────▼──────┐
│   robot_    │  │  action_    │  │  vision_  │  │   serial_   │
│ controller  │  │ sequencer   │  │controller │  │port_finder  │
└─────┬───────┘  └──────┬──────┘  └─────┬─────┘  └─────────────┘
      │                 │                │
      │         ┌───────┴────────┐       │
      │         │                │       │
┌─────▼─────────▼──────┐  ┌──────▼───────▼────┐
│   Serial (PySerial)  │  │  OpenCV (cv2)     │
│   Thor Robot Arm     │  │  Camera/Vision    │
└──────────────────────┘  └───────────────────┘
```

## Tools and useful links
* **QtDesigner** - Used to design the graphical part of gui
* **Python 3.6+** - Required to run Asgard
* **OpenCV** - Computer vision library for object detection
+ **[SKYLOGIC PROJECTS Tutorial](http://projects.skylogic.ca/blog/how-to-install-pyqt5-and-build-your-first-gui-in-python-3-4/)** - How to Install PyQt5 and Build Your First GUI in Python 3.4

## Thanks!

* **[Stack Overflow Community](https://stackoverflow.com/)**: And not only related to this project, but also for having all the answers to all questions I had since I started programming.
* **[Harrison Kinsley](https://twitter.com/Sentdex)** ([sentdex](https://www.youtube.com/user/sentdex) from [pythonprogramming.net](https://pythonprogramming.net)): I learned from you almost everything I know about python. Thanks for that detailed tutorials & examples!
* **[Matthew Dirks](https://github.com/skylogic004)** from [SkyLogic](http://projects.skylogic.ca): Thank you for [this detailed tutorial](http://projects.skylogic.ca/blog/how-to-install-pyqt5-and-build-your-first-gui-in-python-3-4/)! It was incredible easy to make my first GUI in less than an hour following your steps!
* **[Thor Community](https://groups.google.com/forum/#!forum/thor-opensource-3d-printable-robotic-arm)**: For all the support and feedback given! YOU ROCK GUYS!



Do not hesitate on contributing to this project!

## License <img src="doc/By-sa.png" width="100">

All files included in this repository are licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License](http://creativecommons.org/licenses/by-sa/4.0/)
