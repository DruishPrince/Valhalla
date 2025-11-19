# Plugin Development Guide for Asgard Enhanced

This guide will help you create custom plugins for the Thor Robotic Arm control software.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Plugin Structure](#plugin-structure)
4. [Plugin Types](#plugin-types)
5. [Available Hooks](#available-hooks)
6. [Creating Your First Plugin](#creating-your-first-plugin)
7. [Advanced Examples](#advanced-examples)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Overview

Plugins allow you to extend Asgard Enhanced with custom functionality without modifying the core codebase. You can:

- Add custom UI tabs
- Process vision/camera data
- React to robot events (movement, sensor updates)
- Create automated sequences
- Integrate external tools and services
- Process and visualize data in custom ways

## Quick Start

### 1. Create a New Plugin File

Create a new Python file in the `plugins/` directory:

```bash
cd plugins/
touch my_plugin.py
```

### 2. Write the Minimal Plugin Code

```python
from plugin_base import Plugin, PluginMetadata

class MyPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="My Plugin",
            version="1.0.0",
            author="Your Name",
            description="My awesome plugin"
        )

    def initialize(self, gui_app) -> bool:
        self.gui = gui_app
        self.robot = gui_app.robot
        print("My plugin initialized!")
        return True
```

### 3. Restart or Reload

- Restart Asgard Enhanced, OR
- Go to the "Plugins" tab and click "Reload All Plugins"

That's it! Your plugin is now loaded.

## Plugin Structure

Every plugin must:

1. **Import the base class**
   ```python
   from plugin_base import Plugin, PluginMetadata
   ```

2. **Define a class that inherits from Plugin**
   ```python
   class MyPlugin(Plugin):
   ```

3. **Implement the `__init__` method** with metadata
   ```python
   def __init__(self):
       super().__init__()
       self.metadata = PluginMetadata(...)
   ```

4. **Implement the `initialize` method**
   ```python
   def initialize(self, gui_app) -> bool:
       # Your initialization code
       return True  # Return True on success
   ```

## Plugin Types

### Standard Plugin

Use the base `Plugin` class for general-purpose plugins:

```python
from plugin_base import Plugin, PluginMetadata

class MyPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="My Plugin",
            version="1.0.0",
            author="Your Name",
            description="A general plugin"
        )

    def initialize(self, gui_app) -> bool:
        self.gui = gui_app
        return True
```

### Vision Plugin

Use `VisionPlugin` for computer vision tasks:

```python
from plugin_base import VisionPlugin, PluginMetadata
import cv2

class MyVisionPlugin(VisionPlugin):
    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="My Vision Plugin",
            version="1.0.0",
            author="Your Name",
            description="Processes camera frames"
        )

    def initialize(self, gui_app) -> bool:
        self.gui = gui_app
        return True

    def process_frame(self, frame):
        # Process and return the frame
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return gray

    def detect_objects(self, frame):
        # Detect objects and return list
        objects = []
        # ... your detection code ...
        return objects
```

### Sequence Plugin

Use `SequencePlugin` for automated movement sequences:

```python
from plugin_base import SequencePlugin, PluginMetadata

class MySequencePlugin(SequencePlugin):
    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="Custom Sequences",
            version="1.0.0",
            author="Your Name",
            description="Automated movement sequences"
        )

    def initialize(self, gui_app) -> bool:
        self.gui = gui_app
        self.robot = gui_app.robot
        return True

    def get_sequences(self):
        return {
            'wave': self.wave_sequence,
            'pick_and_place': self.pick_and_place_sequence
        }

    def wave_sequence(self):
        # Move the arm in a waving motion
        for _ in range(3):
            self.robot.move_joint('Z', 45, MovementType.G1_LINEAR, 500)
            self.robot.move_joint('Z', -45, MovementType.G1_LINEAR, 500)
```

## Available Hooks

Plugins can hook into various robot events:

### on_robot_connected()
Called when the robot connects.

```python
def on_robot_connected(self):
    print("Robot is now connected!")
    # Do something when robot connects
```

### on_robot_disconnected()
Called when the robot disconnects.

```python
def on_robot_disconnected(self):
    print("Robot disconnected")
    # Clean up, save state, etc.
```

### on_joint_moved(joint_id, angle)
Called whenever a joint moves.

```python
def on_joint_moved(self, joint_id: str, angle: float):
    print(f"Joint {joint_id} moved to {angle}°")
    # React to joint movement
```

### on_kinect_frame(rgb_frame, depth_frame)
Called when new Kinect frames are available.

```python
def on_kinect_frame(self, rgb_frame, depth_frame):
    # Process RGB and depth frames
    if rgb_frame is not None:
        # Do something with the frame
        pass
```

### on_sensor_update(joint_id, sensor_data)
Called when sensor data is updated.

```python
def on_sensor_update(self, joint_id: str, sensor_data: Dict[str, Any]):
    # Process sensor data
    accel = sensor_data.get('acceleration')
    if accel:
        print(f"Joint {joint_id} acceleration: {accel}")
```

## Creating Your First Plugin

Let's create a simple plugin that logs joint movements to a file.

### Step 1: Create the File

Create `plugins/movement_logger.py`:

```python
from plugin_base import Plugin, PluginMetadata
from datetime import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit

class MovementLoggerPlugin(Plugin):
    """Logs all joint movements to a file"""

    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="Movement Logger",
            version="1.0.0",
            author="Your Name",
            description="Logs all joint movements to movement_log.txt"
        )
        self.log_file = "movement_log.txt"
        self.log_widget = None

    def initialize(self, gui_app) -> bool:
        """Initialize the plugin"""
        self.gui = gui_app
        self.robot = gui_app.robot
        print(f"[MovementLogger] Logging to {self.log_file}")
        return True

    def create_widget(self):
        """Create UI for the plugin"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("<h2>Movement Logger</h2>"))
        layout.addWidget(QLabel(f"Logging movements to: {self.log_file}"))

        # Display recent logs
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setMaximumHeight(300)
        layout.addWidget(QLabel("Recent Movements:"))
        layout.addWidget(self.log_widget)

        # Clear log button
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear_log)
        layout.addWidget(clear_btn)

        layout.addStretch()
        return widget

    def on_joint_moved(self, joint_id: str, angle: float):
        """Log when a joint moves"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] Joint {joint_id} → {angle:.2f}°\n"

        # Write to file
        with open(self.log_file, 'a') as f:
            f.write(log_entry)

        # Update UI
        if self.log_widget:
            self.log_widget.append(log_entry.strip())

    def clear_log(self):
        """Clear the log file"""
        open(self.log_file, 'w').close()
        if self.log_widget:
            self.log_widget.clear()
        print("[MovementLogger] Log cleared")

    def shutdown(self):
        """Clean up when plugin is unloaded"""
        print("[MovementLogger] Shutting down")
```

### Step 2: Load the Plugin

1. Restart Asgard Enhanced, or
2. Go to "Plugins" tab → "Reload All Plugins"

### Step 3: Use the Plugin

- Go to the "🔌 Movement Logger" tab to see the UI
- Move any joint in the "Robot Control" tab
- Watch movements appear in the log!

## Advanced Examples

### Example 1: Custom Vision Processing

```python
from plugin_base import VisionPlugin, PluginMetadata
import cv2
import numpy as np

class ColorDetectorPlugin(VisionPlugin):
    """Detects objects of a specific color"""

    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="Color Detector",
            version="1.0.0",
            author="Your Name",
            description="Detects and tracks colored objects"
        )
        # HSV range for red objects
        self.lower_red = np.array([0, 100, 100])
        self.upper_red = np.array([10, 255, 255])

    def initialize(self, gui_app) -> bool:
        self.gui = gui_app
        return True

    def on_kinect_frame(self, rgb_frame, depth_frame):
        """Process frames to detect red objects"""
        if rgb_frame is None:
            return

        # Convert to HSV
        hsv = cv2.cvtColor(rgb_frame, cv2.COLOR_BGR2HSV)

        # Create mask for red color
        mask = cv2.inRange(hsv, self.lower_red, self.upper_red)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)

        # Process largest contour
        if contours:
            largest = max(contours, key=cv2.contourArea)
            if cv2.contourArea(largest) > 500:  # Minimum size
                # Get bounding box
                x, y, w, h = cv2.boundingRect(largest)

                # Get 3D position if depth is available
                if depth_frame is not None:
                    center_x = x + w // 2
                    center_y = y + h // 2
                    depth = depth_frame[center_y, center_x]

                    print(f"Red object at ({center_x}, {center_y}), depth: {depth}mm")

                    # You could command the robot to reach for it!
                    # self.gui.kinematics.inverse_kinematics(...)
```

### Example 2: Automated Calibration Sequence

```python
from plugin_base import SequencePlugin, PluginMetadata
from robot_controller import MovementType
import time

class CalibrationPlugin(SequencePlugin):
    """Automated calibration sequence"""

    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="Auto Calibration",
            version="1.0.0",
            author="Your Name",
            description="Automatic robot calibration sequence"
        )

    def initialize(self, gui_app) -> bool:
        self.gui = gui_app
        self.robot = gui_app.robot
        return True

    def get_sequences(self):
        return {
            'full_calibration': self.full_calibration
        }

    def full_calibration(self):
        """Run full calibration sequence"""
        if not self.robot.is_connected():
            print("Robot not connected!")
            return

        print("Starting calibration...")

        # Home all joints
        print("Step 1: Homing...")
        self.robot.send_homing_command()
        time.sleep(5)

        # Test each joint's range
        joints = ['A', 'B', 'D', 'X', 'Y', 'Z']
        for joint in joints:
            print(f"Step 2: Testing joint {joint}...")

            # Move to minimum
            self.robot.move_joint(joint, -45, MovementType.G1_LINEAR, 300)
            time.sleep(2)

            # Move to maximum
            self.robot.move_joint(joint, 45, MovementType.G1_LINEAR, 300)
            time.sleep(2)

            # Return to center
            self.robot.move_joint(joint, 0, MovementType.G1_LINEAR, 300)
            time.sleep(1)

        print("Calibration complete!")
```

## Best Practices

### 1. Error Handling

Always wrap risky operations in try-except:

```python
def on_kinect_frame(self, rgb_frame, depth_frame):
    try:
        # Your processing code
        pass
    except Exception as e:
        print(f"[MyPlugin] Error processing frame: {e}")
```

### 2. Check Robot Connection

Before sending commands:

```python
def my_function(self):
    if not self.robot.is_connected():
        print("Robot not connected!")
        return
    # Send commands
```

### 3. Use Plugin State

Store configuration in your plugin class:

```python
def __init__(self):
    super().__init__()
    self.my_setting = True
    self.threshold = 100

def create_widget(self):
    # Create UI controls that modify self.my_setting
    pass
```

### 4. Clean Up Resources

Implement shutdown():

```python
def shutdown(self):
    """Clean up when plugin is unloaded"""
    # Close files
    # Stop threads
    # Release resources
    pass
```

### 5. Provide User Feedback

Use the GUI's log console:

```python
self.gui.log_console("Plugin action completed!")
```

## Troubleshooting

### Plugin Not Loading

1. Check the console output when starting Asgard Enhanced
2. Make sure your file is in the `plugins/` directory
3. Ensure your class inherits from `Plugin`
4. Verify `initialize()` returns `True`

### Plugin Loads But No UI Tab

- Make sure `create_widget()` returns a QWidget
- Check that it doesn't return `None`

### Errors When Accessing Robot

- Ensure `self.robot` is set in `initialize()`
- Check if robot is connected before sending commands

### Events Not Triggering

- Make sure your plugin is enabled (check "Plugins" tab)
- Verify you're implementing the correct method name (e.g., `on_joint_moved`, not `on_joint_move`)

### Debugging Tips

Add print statements to see what's happening:

```python
def initialize(self, gui_app) -> bool:
    print("[MyPlugin] Initialize called")
    self.gui = gui_app
    print("[MyPlugin] GUI app stored")
    return True

def on_joint_moved(self, joint_id, angle):
    print(f"[MyPlugin] Joint {joint_id} moved to {angle}°")
```

## Plugin API Reference

### Available Objects in Plugin

After `initialize(gui_app)`, you have access to:

- `self.gui` - Main GUI application
- `self.robot` - RobotController instance
- `self.gui.kinematics` - ThorKinematics for IK/FK
- `self.gui.kinect` - KinectInterface (if connected)
- `self.gui.sequencer` - ActionSequencer
- `self.gui.config` - Configuration dictionary
- `self.gui.log_console(msg)` - Log to console
- `self.gui.joint_controls` - Dict of joint UI controls

### Plugin Methods

**Required:**
- `__init__()` - Initialize and set metadata
- `initialize(gui_app)` - Setup with GUI access

**Optional:**
- `create_widget()` - Return QWidget for custom tab
- `on_robot_connected()` - Handle robot connection
- `on_robot_disconnected()` - Handle robot disconnection
- `on_joint_moved(joint_id, angle)` - Handle joint movement
- `on_kinect_frame(rgb, depth)` - Handle camera frames
- `on_sensor_update(joint_id, data)` - Handle sensor data
- `shutdown()` - Clean up on unload

---

## Need Help?

- Check the example plugins in `plugins/hello_world.py` and `plugins/custom_vision_example.py`
- Look at the plugin_base.py file for the complete API
- Search for existing plugins that do something similar

Happy plugin development!
