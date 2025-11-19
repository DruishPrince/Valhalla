# Kinect RGB-D Camera Integration Guide

Complete guide for integrating Microsoft Kinect cameras with the Thor robotic arm for enhanced 3D vision and depth sensing capabilities.

## Table of Contents
1. [Overview](#overview)
2. [Why Use Kinect?](#why-use-kinect)
3. [Hardware Requirements](#hardware-requirements)
4. [Software Setup](#software-setup)
5. [Kinect Models Comparison](#kinect-models-comparison)
6. [Installation Instructions](#installation-instructions)
7. [Usage Examples](#usage-examples)
8. [Configuration](#configuration)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Topics](#advanced-topics)

---

## Overview

The Microsoft Kinect is an RGB-D camera that provides both color images and depth information. This depth data dramatically improves robotic manipulation by enabling:

-  **Accurate 3D object localization** - Know exact X, Y, Z coordinates
- ⛔ **Obstacle detection and avoidance** - See objects in the path
- 📦 **Volume and shape estimation** - Measure object dimensions
- 🎯 **Precise pick-and-place operations** - Grasp objects accurately
- 🗺️ **Workspace mapping** - Create 3D maps of the environment

---

## Why Use Kinect?

### Regular Camera vs. Kinect

| Feature | Regular Camera | Kinect RGB-D |
|---------|----------------|--------------|
| **Color Image** | ✓ Yes | ✓ Yes |
| **Depth Information** | ✗ No | ✓ Yes |
| **3D Localization** | ✗ Approximate | ✓ Precise |
| **Obstacle Detection** | Limited | ✓ Excellent |
| **Occlusion Handling** | Poor | ✓ Good |
| **Volume Measurement** | ✗ No | ✓ Yes |
| **Point Cloud** | ✗ No | ✓ Yes |

### Real-World Impact

**Without Kinect (monocular vision):**
- Object at unknown depth - might grasp air or crash into table
- No obstacle detection - collisions possible
- Difficult multi-object sorting
- Poor performance with overlapping objects

**With Kinect (RGB-D vision):**
- Accurate 3D position - grasp exactly where object is
- Obstacle avoidance - plan collision-free paths
- Depth-based sorting - handle multiple objects at different distances
- Robust to occlusions and overlapping objects

---

## Hardware Requirements

### Essential Components

| Item | Notes |
|------|-------|
| **Kinect Camera** | v1 (Xbox 360), v2 (Xbox One), or Azure Kinect |
| **Power Supply** | Kinect v1: 12V adapter; v2: USB 3.0 power; Azure: USB-C |
| **USB Cable** | Kinect v1: proprietary; v2: USB 3.0; Azure: USB-C |
| **Computer** | USB 3.0 port (for v2 and Azure); USB 2.0 OK for v1 |

### Kinect Models

#### Kinect v1 (Xbox 360)
- **Best for:** Hobbyists, budget builds
- **Cost:** ~$20-30 (used)
- **Pros:** Cheap, well-supported, works with USB 2.0
- **Cons:** Lower resolution, requires power adapter
- **Depth Range:** 0.8m - 4m
- **Depth Resolution:** 640 x 480

#### Kinect v2 (Xbox One)
- **Best for:** Better accuracy, larger workspace
- **Cost:** ~$50-100 (used)
- **Pros:** Higher resolution, better accuracy, wider FOV
- **Cons:** Requires USB 3.0, more expensive
- **Depth Range:** 0.5m - 4.5m
- **Depth Resolution:** 512 x 424
- **RGB Resolution:** 1920 x 1080

#### Azure Kinect DK
- **Best for:** Professional applications, best quality
- **Cost:** ~$400 (new)
- **Pros:** Best accuracy, multiple modes, supported by Microsoft
- **Cons:** Most expensive
- **Depth Range:** 0.5m - 3.86m (NFOV mode)
- **Depth Resolution:** 640 x 576
- **RGB Resolution:** Up to 3840 x 2160 (4K)

---

## Software Setup

### Dependencies

Different Kinect models require different libraries:

```bash
# For Kinect v1 (Xbox 360)
sudo apt install libfreenect-dev
pip install freenect

# For Kinect v2 (Xbox One)
# Install libfreenect2 first: https://github.com/OpenKinect/libfreenect2
pip install pylibfreenect2

# For Azure Kinect
# Install Azure Kinect SDK: https://github.com/microsoft/Azure-Kinect-Sensor-SDK
pip install pyk4a

# Common dependencies
pip install numpy opencv-python scipy
```

---

## Installation Instructions

### Kinect v1 (Xbox 360) Setup

#### Linux (Ubuntu/Debian)

```bash
# 1. Install libfreenect
sudo apt update
sudo apt install libfreenect-dev freenect

# 2. Install Python bindings
pip install freenect

# 3. Add udev rules for USB access
sudo adduser $USER plugdev
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02ae", MODE="0666"' | sudo tee /etc/udev/rules.d/51-kinect.rules
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02ad", MODE="0666"' | sudo tee -a /etc/udev/rules.d/51-kinect.rules
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02b0", MODE="0666"' | sudo tee -a /etc/udev/rules.d/51-kinect.rules
sudo udevadm control --reload-rules

# 4. Reboot
sudo reboot

# 5. Test Kinect
freenect-glview
```

#### Windows

1. Download and install [libfreenect](https://github.com/OpenKinect/libfreenect/releases)
2. Install Python wrapper: `pip install freenect`
3. Plug in Kinect v1 with power adapter
4. Windows should auto-detect the device

### Kinect v2 (Xbox One) Setup

#### Linux

```bash
# 1. Install dependencies
sudo apt install build-essential cmake pkg-config libturbojpeg0-dev \
    libusb-1.0-0-dev libudev-dev libglfw3-dev

# 2. Clone and build libfreenect2
git clone https://github.com/OpenKinect/libfreenect2.git
cd libfreenect2
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/freenect2
make
make install

# 3. Install Python bindings
pip install pylibfreenect2

# 4. Set up udev rules
sudo cp ../platform/linux/udev/90-kinect2.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger

# 5. Test
./bin/Protonect
```

### Azure Kinect Setup

#### Linux

```bash
# 1. Add Microsoft package repository
curl -sSL https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
sudo apt-add-repository https://packages.microsoft.com/ubuntu/18.04/prod
sudo apt update

# 2. Install Azure Kinect SDK
sudo apt install k4a-tools libk4a1.4 libk4a1.4-dev

# 3. Install Python bindings
pip install pyk4a

# 4. Set up USB rules
wget https://raw.githubusercontent.com/microsoft/Azure-Kinect-Sensor-SDK/develop/scripts/99-k4a.rules
sudo cp 99-k4a.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger

# 5. Test
k4aviewer
```

---

## Usage Examples

### Quick Start

```python
from kinect_interface import KinectInterface

# Auto-detect and open Kinect
kinect = KinectInterface()
if kinect.open():
    print(f"Opened: {kinect.version.value}")

    # Capture RGB-D frame
    frame = kinect.get_rgbd_frame()

    # Access data
    rgb_image = frame.rgb      # Color image
    depth_map = frame.depth    # Depth in millimeters

    # Get depth at specific pixel
    depth_at_center = kinect.get_depth_at_point(frame, 320, 240)
    print(f"Depth at center: {depth_at_center} mm")

    # Convert pixel + depth to 3D point
    x, y, z = kinect.pixel_to_3d(320, 240, depth_at_center)
    print(f"3D position: ({x:.1f}, {y:.1f}, {z:.1f}) mm")

    kinect.close()
```

### 3D Object Detection

```python
from kinect_interface import KinectInterface
from vision_controller_3d import VisionController3D

# Setup
kinect = KinectInterface()
kinect.open()

vision = VisionController3D(kinect)

# Detect red objects with depth
vision.capture_frame()
objects = vision.detect_objects_color(
    lower_hsv=(0, 100, 100),
    upper_hsv=(10, 255, 255)
)

# Access 3D information
for obj in objects:
    print(f"Object: {obj.label}")
    print(f"  2D position: {obj.position_2d}")
    print(f"  3D position: {obj.position_3d}")  # (X, Y, Z) in mm
    print(f"  Depth: {obj.depth} mm")
    print(f"  Volume: {obj.volume} mm³")
```

### Pick and Place with Kinect

```python
from kinect_interface import KinectInterface
from vision_controller_3d import VisionController3D
from robot_controller import RobotController

# Initialize hardware
robot = RobotController()
robot.connect('/dev/ttyUSB0', 115200)

kinect = KinectInterface()
kinect.open()

vision = VisionController3D(kinect)

# Detect object
vision.capture_frame()
objects = vision.detect_objects_color(lower_hsv=(0,100,100), upper_hsv=(10,255,255))

if objects:
    target = objects[0]

    # Get 3D position
    x, y, z = target.position_3d

    # Move above object
    robot.move_to_position(x, y, z + 50, feedrate=300)

    # Descend to grasp
    robot.move_to_position(x, y, z, feedrate=100)

    # Grasp and lift
    # ... gripper control ...
    robot.move_to_position(x, y, z + 100, feedrate=200)

kinect.close()
robot.disconnect()
```

### Complete Examples

Run the comprehensive example script:

```bash
python3 example_kinect_manipulation.py
```

This provides interactive examples for:
1. Accurate pick and place with depth
2. Obstacle avoidance
3. Volume measurement
4. Depth-based sorting
5. Workspace mapping
6. Collision-free path planning

---

## Configuration

### Using config_manager.py

```python
from config_manager import get_config, get_kinect_config

config = get_config()

# Enable Kinect
config.set('kinect.enabled', True)

# Set Kinect version (or 'auto' for auto-detection)
config.set('kinect.version', 'v2')  # 'v1', 'v2', 'azure', or 'auto'

# Configure depth range
config.set('kinect.min_depth_mm', 500)
config.set('kinect.max_depth_mm', 4000)

# Set detection mode
config.set('kinect.detection_mode', 'depth_clustering')

# Get config
kinect_config = get_kinect_config()
print(kinect_config)
```

### Configuration Options

```json
{
  "kinect": {
    "enabled": true,
    "version": "auto",
    "use_depth": true,
    "min_depth_mm": 500,
    "max_depth_mm": 4000,
    "depth_smoothing_window": 5,
    "min_object_area": 500,
    "max_object_area": 50000,
    "point_cloud_enabled": true,
    "save_point_clouds": false,
    "detection_mode": "color",
    "visualization": {
      "show_depth": true,
      "show_point_cloud": false,
      "depth_colormap": "JET",
      "overlay_detections": true
    }
  }
}
```

---

## Troubleshooting

### Kinect Not Detected

**Problem:** `Failed to open Kinect camera`

**Solutions:**
1. Check USB connection
2. Ensure Kinect is powered (v1 requires 12V adapter)
3. Check library installation:
   ```bash
   # For v1
   python3 -c "import freenect; print('OK')"

   # For v2
   python3 -c "import pylibfreenect2; print('OK')"

   # For Azure
   python3 -c "import pyk4a; print('OK')"
   ```
4. Check udev rules (Linux):
   ```bash
   ls -l /dev/bus/usb/*/*  # Should show Kinect device
   ```

### Poor Depth Quality

**Problem:** Depth map is noisy or has holes

**Solutions:**
1. **Lighting:** Avoid direct sunlight and IR interference
2. **Surface:** Shiny/transparent objects don't reflect IR well
3. **Distance:** Keep objects within optimal range (0.5m - 3m)
4. **Smoothing:** Increase `depth_smoothing_window`:
   ```python
   vision.depth_smoothing_window = 7  # Default: 5
   ```
5. **Material:** Some materials (glass, mirrors, black surfaces) absorb IR

### USB 3.0 Bandwidth Issues (Kinect v2)

**Problem:** Frame drops or disconnections

**Solutions:**
1. Use dedicated USB 3.0 controller (not shared with other devices)
2. Disable USB selective suspend:
   ```bash
   # Linux
   echo 'on' | sudo tee /sys/bus/usb/devices/*/power/control
   ```
3. Lower resolution or frame rate
4. Update USB 3.0 drivers

### Permission Denied (Linux)

**Problem:** `Permission denied: '/dev/bus/usb/...'`

**Solution:**
```bash
# Add user to plugdev group
sudo usermod -a -G plugdev $USER

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Reboot
sudo reboot
```

---

## Advanced Topics

### Point Cloud Processing

```python
# Capture full workspace point cloud
frame = kinect.get_rgbd_frame()
point_cloud = frame.get_point_cloud(kinect.camera_matrix)

# point_cloud is Nx6 array: [X, Y, Z, R, G, B]
print(f"Points: {len(point_cloud)}")

# Save for external processing
import numpy as np
np.save('workspace.npy', point_cloud)

# Or export to PLY format for visualization
def save_ply(filename, points):
    with open(filename, 'w') as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(points)}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("property uchar red\n")
        f.write("property uchar green\n")
        f.write("property uchar blue\n")
        f.write("end_header\n")
        for p in points:
            f.write(f"{p[0]} {p[1]} {p[2]} {int(p[3]*255)} {int(p[4]*255)} {int(p[5]*255)}\n")

save_ply('workspace.ply', point_cloud)
# View with MeshLab, CloudCompare, or Open3D
```

### Camera Calibration

For accurate robot-to-camera transformation:

```python
from vision_controller import CoordinateTransformer

# Create transformer
transformer = CoordinateTransformer()

# Define calibration points (pixel coords -> robot coords)
calibration_points = [
    ((100, 100), (50, 50, 0)),    # Top-left
    ((540, 100), (250, 50, 0)),   # Top-right
    ((100, 380), (50, 250, 0)),   # Bottom-left
    ((540, 380), (250, 250, 0)),  # Bottom-right
]

# Calibrate
transformer.calibrate(calibration_points)

# Now use with 3D vision
vision = VisionController3D(kinect, transformer)

# Detected objects will have position_robot set
objects = vision.detect_objects_color(...)
for obj in objects:
    print(f"Robot coordinates: {obj.position_robot}")
```

### Multi-Camera Setup

For larger workspaces, use multiple Kinects:

```python
# Open specific Kinect by index
kinect1 = KinectInterface()
kinect1.open()  # First device

kinect2 = KinectInterface()
kinect2.open()  # Second device (if available)

# Process both streams
frame1 = kinect1.get_rgbd_frame()
frame2 = kinect2.get_rgbd_frame()

# Merge point clouds (requires calibration between cameras)
pc1 = frame1.get_point_cloud(kinect1.camera_matrix)
pc2 = frame2.get_point_cloud(kinect2.camera_matrix)
```

### Integration with ROS

For ROS users, publish Kinect data:

```python
import rospy
from sensor_msgs.msg import Image, PointCloud2
from cv_bridge import CvBridge

rospy.init_node('kinect_publisher')
rgb_pub = rospy.Publisher('/kinect/rgb/image_raw', Image, queue_size=10)
depth_pub = rospy.Publisher('/kinect/depth/image_raw', Image, queue_size=10)

bridge = CvBridge()
kinect = KinectInterface()
kinect.open()

rate = rospy.Rate(30)  # 30 Hz
while not rospy.is_shutdown():
    frame = kinect.get_rgbd_frame()

    # Publish RGB
    rgb_msg = bridge.cv2_to_imgmsg(frame.rgb, 'bgr8')
    rgb_pub.publish(rgb_msg)

    # Publish depth
    depth_msg = bridge.cv2_to_imgmsg(frame.depth, 'passthrough')
    depth_pub.publish(depth_msg)

    rate.sleep()
```

---

## Performance Considerations

### Frame Rate

| Kinect Model | Max FPS | Typical FPS |
|--------------|---------|-------------|
| v1           | 30      | 30          |
| v2           | 30      | 30          |
| Azure        | 30      | 30          |

For manipulation, 10-15 FPS is usually sufficient.

### Latency

- **v1:** ~30ms capture + processing
- **v2:** ~33ms capture + processing
- **Azure:** ~33ms capture + processing

Total system latency (capture + detection + robot command): ~100-200ms

### Computational Requirements

- **CPU:** Multi-core recommended for point cloud processing
- **RAM:** 4GB minimum, 8GB+ recommended
- **USB:** Dedicated USB 3.0 controller for v2 and Azure

---

## Resources

### Documentation
- [libfreenect (Kinect v1)](https://openkinect.org)
- [libfreenect2 (Kinect v2)](https://github.com/OpenKinect/libfreenect2)
- [Azure Kinect SDK](https://github.com/microsoft/Azure-Kinect-Sensor-SDK)
- [pyk4a Documentation](https://github.com/etiennedub/pyk4a)

### Community
- [OpenKinect Forum](https://openkinect.org/wiki/Main_Page)
- [Azure Kinect GitHub Discussions](https://github.com/microsoft/Azure-Kinect-Sensor-SDK/discussions)

### Example Projects
- [Kinect 3D Scanning](https://github.com/OpenKinect/libfreenect/tree/master/examples)
- [Object Recognition with Kinect](https://github.com/ros-drivers/kinect_ros)
- [Point Cloud Processing](http://www.open3d.org/)

---

**✓ You're now ready to use Kinect for enhanced robotic vision!**

For questions or issues, consult the troubleshooting section or check the community forums.
