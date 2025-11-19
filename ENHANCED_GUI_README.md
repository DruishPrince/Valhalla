# Asgard Enhanced GUI

Modern, feature-complete graphical interface for Thor robotic arm control with integrated Kinect depth sensing, ADXL345 sensor feedback, and advanced manipulation capabilities.

## Features

### 🤖 Robot Control Tab
- **Connection Management**: Easy serial port selection and connection
- **Joint Control**: Individual joint sliders with precise angle control
- **Quick Actions**: Home, Zero Position, Move All Joints
- **G-code Console**: Direct command input for advanced users
- **Real-time Status**: Visual connection indicators

### 📷 Kinect Vision Tab
- **RGB-D Camera Support**: Kinect v1, v2, and Azure Kinect
- **Live Video Feed**: Dual display (RGB + Depth visualization)
- **3D Object Detection**: Three detection modes:
  - Color-based detection
  - Contour/edge detection
  - Depth clustering
- **Real-time Results**: Object position, depth, and volume display
- **Interactive Visualization**: Detection overlays on live feed

### 📡 Sensors Tab
- **Gateway Support**: Pi Zero 2W and Pico sensor gateways
- **Connection Modes**: Serial (USB) or Network (WiFi)
- **Live Sensor Readings**: Real-time joint angle feedback
- **Calibration Tools**: One-click sensor calibration
- **Closed-Loop Control**: Enable/disable with adjustable parameters
  - Maximum position error threshold
  - Correction gain tuning

### 🎬 Action Sequencer Tab
- **Record & Playback**: Capture robot movement sequences
- **Sequence Management**: Save/load sequences as JSON
- **Sequence Info**: Duration and action count display
- **Timestamp Accuracy**: Precise playback timing

### ⚙️ Configuration Tab
- **Board Selection**: Generic GRBL or FLY Super ♾️ Pro
- **Config Display**: View current configuration
- **Hot Reload**: Reload configuration without restarting

## Installation

### Requirements
```bash
pip install PyQt5>=5.15.0
pip install pyserial>=3.5
pip install opencv-python>=4.5.0
pip install numpy>=1.21.0
pip install matplotlib>=3.3.0
pip install scipy>=1.7.0

# Optional: Kinect support (choose one)
pip install freenect  # For Kinect v1
pip install pylibfreenect2  # For Kinect v2
pip install pyk4a  # For Azure Kinect
```

### Quick Start

**Windows:**
```cmd
# Double-click run_asgard_enhanced.bat
# Or from command prompt:
run_asgard_enhanced.bat
```

**Linux/Mac:**
```bash
# Make executable (first time only)
chmod +x run_asgard_enhanced.sh

# Run
./run_asgard_enhanced.sh
```

**Manual:**
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Run
python asgard_enhanced.py
```

## Usage Guide

### 1. Connecting the Robot

1. Select your COM port from the dropdown
2. Click "Refresh" if port doesn't appear
3. Click "Connect"
4. Status bar shows "Robot: Connected ✓"

### 2. Controlling Joints

**Individual Joint Control:**
- Use slider or spinbox to set angle
- Click "Go" button to move that joint
- Range: -180° to +180°

**Move All Joints:**
- Set all desired angles
- Click "Move All Joints"
- All joints move simultaneously

**Quick Actions:**
- **Home All**: Runs homing cycle (G28)
- **Zero Position**: Moves all joints to 0°

### 3. Using Kinect Vision

**Setup:**
1. Switch to "Kinect Vision" tab
2. Click "Connect Kinect"
3. Camera auto-detects (v1, v2, or Azure)
4. Live RGB and depth feeds appear

**3D Object Detection:**
1. Place object in view
2. Select detection mode:
   - **Color**: Detects red objects (adjustable in code)
   - **Contour**: Edge-based detection
   - **Depth Clustering**: Groups by depth
3. Click "Detect Objects"
4. Results show:
   - 2D pixel coordinates
   - 3D position (X, Y, Z in mm)
   - Depth in meters
   - Volume in cm³

**Pick-and-Place:**
- Detection results include 3D coordinates
- Use these coordinates with robot control
- Depth information ensures accurate grasping

### 4. Sensor Gateway

**For FLY Super ♾️ Pro boards without exposed I2C:**

1. Switch to "Sensors" tab
2. Select gateway type (Pi Zero 2W or Pico)
3. Choose connection:
   - **Serial**: Enter COM port (e.g., COM4)
   - **Network**: Enter IP (e.g., 192.168.1.100)
4. Click "Connect Gateway"
5. Live sensor readings appear

**Calibration:**
1. Move robot to home position
2. Keep stationary
3. Click "Calibrate All Sensors"
4. Wait for completion

**Closed-Loop Control:**
1. Check "Enable Closed-Loop"
2. Set max error (default: 5°)
3. Set correction gain (default: 0.5)
4. Robot automatically corrects position errors

### 5. Recording Sequences

**Record:**
1. Switch to "Action Sequencer" tab
2. Enter sequence name
3. Click "Start Recording"
4. Perform robot movements
5. Click "Stop Recording"
6. Click "Save Sequence"

**Playback:**
1. Click "Load Sequence"
2. Select JSON file
3. Review sequence info
4. Click "Play Sequence"
5. Robot repeats recorded movements

## Advanced Features

### Multiple Detection Modes

**Color Detection:**
- Best for: Known colored objects
- Pros: Fast, simple
- Cons: Lighting dependent

**Contour Detection:**
- Best for: Objects with clear edges
- Pros: Lighting independent
- Cons: Cluttered backgrounds difficult

**Depth Clustering:**
- Best for: Overlapping or occluded objects
- Pros: Robust to occlusions
- Cons: Requires depth camera

### Real-Time Sensor Feedback

With ADXL345 sensors and closed-loop control:
- Robot knows actual joint positions
- Automatic error correction
- Improved accuracy
- Detects mechanical issues

### Network Sensor Gateway

For wireless operation:
1. Configure Pi Zero 2W WiFi
2. Run gateway on Pi: `python3 sensor_gateway_pi.py --network`
3. In GUI, select "Network" mode
4. Enter Pi's IP address
5. Connect wirelessly

## Configuration

Edit `asgard_config.json` for customization:

```json
{
  "serial": {
    "port": "COM3",
    "baudrate": 115200
  },
  "kinect": {
    "enabled": true,
    "version": "auto",
    "detection_mode": "color"
  },
  "sensors": {
    "enabled": true,
    "mode": "gateway"
  },
  "sensor_gateway": {
    "connection_mode": "serial",
    "serial_port": "COM4"
  }
}
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Ctrl+Q | Quit application |
| Ctrl+H | Home robot |
| Ctrl+0 | Zero position |
| Ctrl+R | Start/stop recording |
| Ctrl+P | Play sequence |

## Troubleshooting

### Robot Won't Connect
- Check COM port selection
- Verify USB cable connection
- Try different USB port
- Check Device Manager (Windows)

### Kinect Not Detected
- Install correct driver for your model
- Kinect v2/Azure need USB 3.0
- Check USB power (v1 needs 12V adapter)
- Try different USB port

### No Sensor Data
- Verify gateway is running
- Check COM port/IP address
- Ensure I2C wiring is correct
- Run `i2cdetect` on Pi to verify sensors

### Poor Depth Quality
- Avoid direct sunlight
- Keep within range (0.5m - 3m)
- Clean Kinect IR sensor
- Avoid reflective surfaces

### Closed-Loop Not Working
- Calibrate sensors first
- Check sensor readings are updating
- Verify robot is connected
- Reduce correction gain if oscillating

## Tips & Best Practices

1. **Always home robot** after power-on for accurate positions
2. **Calibrate sensors** at known position (usually home)
3. **Save sequences** before experimenting - easy to restore
4. **Use depth clustering** for complex scenes with occlusions
5. **Network mode** useful for cable management
6. **Lower correction gain** (0.3-0.4) if closed-loop oscillates
7. **Record sequences slowly** for smoother playback
8. **Clean Kinect lens** regularly for best depth quality

## Comparison: Original vs Enhanced

| Feature | Original Asgard | Asgard Enhanced |
|---------|----------------|-----------------|
| Joint Control | ✓ Yes | ✓ Yes (improved) |
| Camera Support | Basic webcam | ✓ Kinect RGB-D |
| Depth Sensing | ✗ No | ✓ Yes |
| 3D Detection | ✗ No | ✓ Yes |
| Sensor Feedback | ✗ No | ✓ ADXL345 support |
| Closed-Loop | ✗ No | ✓ Yes |
| Gateway Support | ✗ No | ✓ Pi/Pico |
| Sequencer | Basic | ✓ Enhanced |
| Modern UI | Basic | ✓ Tabbed interface |

## Support

For issues, see:
- **SETUP_GUIDE.md** - Complete installation instructions
- **KINECT_GUIDE.md** - Kinect-specific help
- **SENSOR_GUIDE.md** - ADXL345 sensor setup
- **Troubleshooting section above**

## Future Enhancements

Planned features:
- [ ] 3D point cloud visualization
- [ ] Custom detection color picker
- [ ] Sequence editor (modify recorded sequences)
- [ ] Multiple robot support
- [ ] ROS integration
- [ ] Web interface option

---

**Version:** 1.0
**Author:** Asgard Development Team
**License:** See LICENSE file

**Enjoy your enhanced robotic arm control! 🤖**
