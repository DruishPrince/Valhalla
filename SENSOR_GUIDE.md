# ADXL345 Sensor Setup Guide

Complete guide for adding ADXL345 3-axis accelerometer sensors to your Thor robotic arm for real-time joint angle feedback and proprioception.

## Table of Contents
1. [Overview](#overview)
2. [Hardware Requirements](#hardware-requirements)
3. [Wiring and Installation](#wiring-and-installation)
4. [Software Setup](#software-setup)
5. [Calibration](#calibration)
6. [Usage Examples](#usage-examples)
7. [FLY Super ♾️ Pro Board Setup](#fly-super-pro-board-setup)
8. [Troubleshooting](#troubleshooting)

---

## FLY Super ♾️ Pro Board Setup

### Overview

The **Mellow FLY Super ♾️ Pro** is a high-performance 8-axis controller board designed for 3D printers and CNC machines. However, it doesn't expose I2C pins for direct sensor connection. This guide shows you how to use an external gateway (Raspberry Pi Zero 2W or Pico) to read sensors and transmit data to your main computer.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Main Computer                          │
│  ┌──────────────────┐         ┌─────────────────────────┐  │
│  │ Robot Controller │         │ Sensor Gateway Client   │  │
│  │   (Python)       │         │     (Python)            │  │
│  └────────┬─────────┘         └──────────┬──────────────┘  │
│           │                              │                  │
└───────────┼──────────────────────────────┼──────────────────┘
            │                              │
       USB Serial                     USB Serial
            │                              │
    ┌───────▼────────────┐         ┌───────▼─────────────────┐
    │  FLY Super 8 Pro   │         │  Pi Zero 2W / Pico      │
    │  (Robot Control)   │         │  (Sensor Gateway)       │
    │  /dev/ttyUSB0      │         │  /dev/ttyUSB1           │
    └────────────────────┘         └───────┬─────────────────┘
                                           │
                                         I2C Bus
                                           │
                      ┌────────────────────┼────────────────┐
                      │                    │                │
                ┌─────▼─────┐      ┌──────▼──────┐   ┌─────▼─────┐
                │ ADXL345   │      │  ADXL345    │   │ ADXL345   │
                │ (Joint A) │      │  (Joint B)  │   │ (Joint D) │
                │  0x53     │      │   0x1D      │   │  0x53*    │
                └───────────┘      └─────────────┘   └───────────┘
                                                      *via I2C mux
```

### Hardware Options

You have two options for the sensor gateway:

#### Option 1: Raspberry Pi Zero 2W (Recommended)
**Pros:**
- Full Linux OS - easier to debug and modify
- More processing power
- Can run Python scripts directly
- Built-in WiFi (can also transmit over network)

**Cons:**
- More expensive (~$15)
- Slightly larger
- Higher power consumption

**Use when:** You want ease of development and debugging

#### Option 2: Raspberry Pi Pico
**Pros:**
- Very cheap (~$4)
- Tiny and low power
- Dedicated to sensor reading (no OS overhead)
- Multiple I2C buses (I2C0 and I2C1)

**Cons:**
- MicroPython environment (more limited)
- Harder to debug
- USB serial only (no network)

**Use when:** You want lowest cost and smallest footprint

### Hardware Setup

#### Components Needed

| Item | Quantity | Notes |
|------|----------|-------|
| Mellow FLY Super ♾️ Pro | 1 | Your robot controller |
| Raspberry Pi Zero 2W **or** Pico | 1 | Sensor gateway |
| ADXL345 breakout boards | 3-6 | One per moving joint |
| USB cables | 2 | Connect both boards to PC |
| MicroSD card (Pi Zero only) | 1 | 8GB+ for Raspberry Pi OS Lite |
| I2C multiplexer (optional) | 1 | TCA9548A for >2 sensors |
| Jumper wires | ~20 | I2C connections |

### Wiring - Pi Zero 2W Gateway

```
Raspberry Pi Zero 2W                ADXL345 Sensors
┌─────────────────────┐
│  PIN 1  (3.3V) ─────┼───┬─── Sensor 1 VCC (0x53)
│  PIN 6  (GND)  ─────┼───┼─── Sensor 1 GND
│  PIN 3  (SDA)  ─────┼───┼─── Sensor 1 SDA
│  PIN 5  (SCL)  ─────┼───┼─── Sensor 1 SCL
│                     │   │    Sensor 1 SDO ─── GND
│                     │   │
│                     │   ├─── Sensor 2 VCC (0x1D)
│                     │   ├─── Sensor 2 GND
│                     │   ├─── Sensor 2 SDA
│                     │   ├─── Sensor 2 SCL
│                     │   │    Sensor 2 SDO ─── 3.3V
│                     │   │
│  USB Port ──────────┼───┘    (For more sensors, use I2C mux)
│  (to main PC)       │
└─────────────────────┘
```

### Wiring - Pico Gateway

```
Raspberry Pi Pico                   ADXL345 Sensors
┌─────────────────────┐
│  PIN 36 (3V3 OUT)───┼───┬─── Sensor 1 VCC (I2C0, 0x53)
│  PIN 38 (GND)   ────┼───┼─── Sensor 1 GND
│  PIN 6  (GP4/SDA0)──┼───┼─── Sensor 1 SDA
│  PIN 7  (GP5/SCL0)──┼───┼─── Sensor 1 SCL
│                     │   │    Sensor 1 SDO ─── GND
│                     │   │
│  PIN 19 (GP14/SDA1)─┼───┼─── Sensor 2 SDA (I2C1, 0x53)
│  PIN 20 (GP15/SCL1)─┼───┼─── Sensor 2 SCL
│                     │   │    Sensor 2 VCC ─── 3.3V
│                     │   │    Sensor 2 GND ─── GND
│                     │   │    Sensor 2 SDO ─── GND
│                     │   │
│  USB Port ──────────┼───┘    Sensor 3 (I2C0, 0x1D)
│  (to main PC)       │        Sensor 3 SDO ─── 3.3V
└─────────────────────┘
```

**Note:** Pico has 2 I2C buses, allowing up to 4 sensors without multiplexer

### Software Setup - Pi Zero 2W

#### 1. Install Raspberry Pi OS Lite

```bash
# On your PC, flash Raspberry Pi OS Lite to SD card
# Use Raspberry Pi Imager: https://www.raspberrypi.com/software/

# Enable SSH and configure WiFi during imaging
```

#### 2. Enable I2C

```bash
# SSH into Pi Zero
ssh pi@raspberrypi.local

# Enable I2C
sudo raspi-config
# Navigate to: Interface Options → I2C → Enable

# Reboot
sudo reboot
```

#### 3. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python dependencies
sudo apt install python3-pip python3-smbus i2c-tools -y

# Install required Python packages
pip3 install smbus2 pyserial
```

#### 4. Test I2C Connection

```bash
# Scan for I2C devices
sudo i2cdetect -y 1

# You should see your ADXL345 sensors:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 00:          -- -- -- -- -- -- -- -- -- -- -- -- --
# 10: -- -- -- -- -- -- -- -- -- -- -- -- -- 1d -- --
# 20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 50: -- -- -- 53 -- -- -- -- -- -- -- -- -- -- -- --
```

#### 5. Upload Gateway Script

```bash
# On your main PC, copy the gateway script to Pi Zero
scp sensor_gateway_pi.py pi@raspberrypi.local:~/

# SSH into Pi and run
ssh pi@raspberrypi.local
python3 sensor_gateway_pi.py --serial /dev/ttyACM0 --baud 115200
```

#### 6. Configure Auto-Start (Optional)

```bash
# Create systemd service for auto-start on boot
sudo nano /etc/systemd/system/sensor-gateway.service
```

Add:
```ini
[Unit]
Description=ADXL345 Sensor Gateway
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
ExecStart=/usr/bin/python3 /home/pi/sensor_gateway_pi.py --serial /dev/ttyACM0
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable sensor-gateway.service
sudo systemctl start sensor-gateway.service
```

### Software Setup - Pico

#### 1. Install MicroPython

1. Download MicroPython UF2 file: https://micropython.org/download/rp2-pico/
2. Hold BOOTSEL button on Pico while plugging in USB
3. Drag UF2 file to RPI-RP2 drive that appears
4. Pico will reboot with MicroPython installed

#### 2. Upload Gateway Script

Using Thonny IDE (recommended):

```bash
# Install Thonny
sudo apt install thonny

# Or download from: https://thonny.org/
```

1. Open Thonny
2. Select Interpreter: MicroPython (Raspberry Pi Pico)
3. Open `sensor_gateway_pico.py`
4. Save as `main.py` on Pico (File → Save As → Raspberry Pi Pico)
5. Reset Pico - it will auto-start the gateway

Alternatively, use `mpremote`:

```bash
# Install mpremote
pip install mpremote

# Upload script
mpremote connect /dev/ttyACM0 fs cp sensor_gateway_pico.py :main.py

# Reset Pico
mpremote reset
```

### Main Computer Setup

#### 1. Configure FLY Board in Asgard

Edit `asgard_config.json` or use Python:

```python
from config_manager import set_current_board, get_config

# Set FLY board as current
set_current_board('fly_super_8_pro')

# Configure sensor gateway
config = get_config()
config.set('sensors.enabled', True)
config.set('sensors.mode', 'gateway')
config.set('sensors.gateway_type', 'pi_zero')  # or 'pico'

config.set('sensor_gateway.connection_mode', 'serial')
config.set('sensor_gateway.serial_port', '/dev/ttyUSB1')  # Gateway port
config.set('sensor_gateway.serial_baudrate', 115200)
```

#### 2. Test Connection

```bash
# Run the FLY board example
python3 example_fly_board_setup.py
```

Expected output:
```
============================================================
FLY Super ♾️ Pro Board Setup
============================================================

Board: Mellow FLY Super ♾️ Pro Board
Requires sensor gateway: True

1. Setting up robot controller...
   ✓ Robot connected on /dev/ttyUSB0

2. Setting up sensor gateway...
   ✓ Sensor gateway connected
   Waiting for sensor data...
   ✓ Receiving data from 3 sensors

3. Creating sensor integration...
   ✓ Integration ready
```

### Calibration

After hardware setup, calibrate sensors:

```python
from sensor_gateway_client import SensorGatewayClient, GatewayConfig

# Connect to gateway
config = GatewayConfig(
    mode='serial',
    serial_port='/dev/ttyUSB1',
    serial_baudrate=115200
)

client = SensorGatewayClient(config)
client.connect()

# Calibrate all sensors at home position
# (Make sure robot is at 0° for all joints)
client.calibrate_all()

print("Calibration complete!")
```

Or use the interactive example:

```bash
python3 example_fly_board_setup.py
# Select option 1: Calibrate sensors
```

### Testing

#### Quick Serial Test

Test gateway communication:

```bash
# On gateway (Pi/Pico), data should be streaming
# On main PC, listen to serial port
python3 -c "
import serial
s = serial.Serial('/dev/ttyUSB1', 115200)
while True:
    print(s.readline().decode().strip())
"
```

You should see JSON data like:
```json
{"timestamp": 1234567.89, "joints": {"A": {"angle": 0.1, "accel_x": 0.002, ...}}}
```

#### Full Integration Test

```bash
# Run complete test
python3 example_fly_board_setup.py

# Menu options:
# 1. Calibrate sensors
# 2. Test basic movement
# 3. Test closed-loop control
# 4. Show system status
```

### Performance Considerations

- **Update Rate**: Gateway runs at 10 Hz by default (configurable)
- **Serial Bandwidth**: 115200 baud is sufficient for 3-6 sensors at 10 Hz
- **Latency**: ~100ms typical (USB serial + processing)
- **Network Option**: Pi Zero can also transmit via WiFi (TCP/UDP)

### Power Considerations

- Pi Zero 2W: ~150-200mA @ 5V (0.75-1W)
- Pico: ~20-30mA @ 5V (0.1-0.15W)
- Each ADXL345: ~140μA @ 3.3V (0.0005W)

Total power for gateway + 3 sensors:
- Pi Zero setup: ~1W
- Pico setup: ~0.15W

---

## Overview

### What Are ADXL345 Sensors?

The ADXL345 is a small, thin, ultralow power, 3-axis accelerometer with high resolution (13-bit) measurement. By mounting one on each moving joint of your robot arm, you can:

- **Know the actual position** of each joint in real-time
- **Detect position errors** between commanded and actual angles
- **Implement closed-loop control** for precise positioning
- **Monitor robot health** by detecting unexpected movements
- **Provide proprioception** - the robot knows where it is

### How It Works

The ADXL345 measures acceleration in three axes (X, Y, Z). When stationary or moving slowly, it primarily measures gravity's pull (~1g downward). By analyzing which direction gravity is pulling, we can calculate the orientation (roll and pitch angles) of each joint.

---

## Hardware Requirements

### Essential Components

| Item | Quantity | Notes |
|------|----------|-------|
| ADXL345 breakout boards | 3-6 | One per moving joint |
| Jumper wires | ~20 | For I2C connections |
| Mounting hardware | As needed | Screws, brackets, or 3D printed mounts |

### Recommended Tools

- Soldering iron (if headers need to be soldered)
- Multimeter (for testing connections)
- Small screwdriver
- Heat shrink tubing or electrical tape

### Where to Buy

- Adafruit ADXL345 breakout: https://www.adafruit.com/product/1231
- SparkFun ADXL345 breakout: https://www.sparkfun.com/products/9836
- Generic ADXL345 modules: Available on Amazon, AliExpress

---

## Wiring and Installation

### I2C Address Configuration

Each ADXL345 on the same I2C bus needs a unique address. The ADXL345 supports two addresses:

- **0x53** (83 decimal) - When SDO pin is connected to GND (default)
- **0x1D** (29 decimal) - When SDO pin is connected to VCC

For more than 2 sensors, you'll need:
- Multiple I2C buses (if your controller supports it)
- An I2C multiplexer (like TCA9548A)

### Basic Wiring Diagram

```
Raspberry Pi / Controller          ADXL345 Sensor
┌───────────────────┐              ┌──────────────┐
│                   │              │              │
│  3.3V ────────────┼──────────────┤ VCC          │
│                   │              │              │
│  GND  ────────────┼──────────────┤ GND          │
│                   │              │              │
│  SDA  ────────────┼──────────────┤ SDA          │
│                   │              │              │
│  SCL  ────────────┼──────────────┤ SCL          │
│                   │              │              │
│                   │     ┌────────┤ SDO          │
│  GND or 3.3V ─────┼─────┘        │              │
│  (address select) │              │              │
└───────────────────┘              └──────────────┘
```

### Multiple Sensors

For connecting multiple sensors on one I2C bus:

```
Controller
    │
    ├─── VCC ───┬─── Sensor 1 (VCC)
    │           ├─── Sensor 2 (VCC)
    │           └─── Sensor 3 (VCC)
    │
    ├─── GND ───┬─── Sensor 1 (GND)
    │           ├─── Sensor 2 (GND)
    │           └─── Sensor 3 (GND)
    │
    ├─── SDA ───┬─── Sensor 1 (SDA)
    │           ├─── Sensor 2 (SDA)
    │           └─── Sensor 3 (SDA)
    │
    └─── SCL ───┬─── Sensor 1 (SCL)
                ├─── Sensor 2 (SCL)
                └─── Sensor 3 (SCL)

Address Configuration:
- Sensor 1 SDO → GND  (address 0x53)
- Sensor 2 SDO → VCC  (address 0x1D)
- Sensor 3 → Use I2C bus 2 or multiplexer
```

### Mounting Sensors on Joints

For accurate angle sensing, sensors should be mounted:

1. **Rigidly** - No flex or vibration
2. **Aligned** - One axis aligned with joint rotation
3. **Protected** - From impacts and debris

#### Mounting Tips:

- **3D Print custom mounts** specific to your robot
- **Use hot glue** for temporary testing
- **Use screws** for permanent installation
- **Label each sensor** with its joint ID
- **Route wires carefully** to avoid joint interference

#### Example Mount Locations:

```
Base Joint (A):
    Mount on rotating platform, aligned with vertical axis

Shoulder Joint (B):
    Mount on upper arm link, perpendicular to rotation axis

Elbow Joint (D):
    Mount on forearm link, perpendicular to rotation axis

Wrist Joints (X, Y):
    Mount on wrist assembly, aligned with respective axes
```

---

## Software Setup

### 1. Install Dependencies

```bash
pip install smbus2
```

### 2. Enable I2C on Raspberry Pi

```bash
sudo raspi-config
# Navigate to: Interfacing Options → I2C → Enable

# Verify I2C is enabled
ls /dev/i2c-*
```

### 3. Test I2C Communication

```bash
# Install i2c-tools
sudo apt-get install i2c-tools

# Scan for devices
i2cdetect -y 1

# You should see your ADXL345 addresses (53, 1D, etc.)
```

### 4. Test Basic Sensor Reading

```python
python adxl345_sensor.py
```

Expected output:
```
=== ADXL345 Sensor Test ===

✓ ADXL345 connected at 0x53

Reading sensor data...
Sample 1:
  Accel: ( 0.012, -0.005,  0.998) g
  Magnitude: 0.999 g
  Orientation: Roll=  -0.3° Pitch=   0.7°
...
```

---

## Calibration

### Why Calibrate?

Calibration ensures sensors accurately measure joint angles by:
1. Compensating for mounting imperfections
2. Setting zero reference points
3. Removing sensor bias and offset

### Calibration Methods

#### Method 1: Interactive Calibration

```bash
python calibrate_sensors.py
```

Follow the prompts to:
1. Configure sensors
2. Position each joint at 0°
3. Calibrate one by one
4. Save configuration

#### Method 2: Robot-Assisted Calibration

```python
from sensor_integration import create_integrated_system

system = create_integrated_system(simulate_sensors=False)
system.calibrate_sensors_at_home()
system.sensors.save_config('sensor_config.json')
```

### Calibration Procedure

For each joint:

1. **Move joint to 0° position**
   - Use robot homing function OR
   - Manually position and measure with protractor

2. **Keep joint stationary**
   - No movement during calibration
   - 5-10 seconds

3. **Run calibration**
   ```python
   manager.calibrate_joint('A', num_samples=200)
   ```

4. **Verify calibration**
   - Check that measured angle ≈ 0°
   - Re-calibrate if error > 2°

### Saving Calibration

```python
manager.save_config('sensor_config.json')
```

Configuration is saved in JSON format:
```json
{
  "sensors": {
    "A": {
      "joint_id": "A",
      "joint_name": "Base",
      "i2c_address": 83,
      "axis_mapping": {"primary": "roll", "secondary": "pitch"},
      "zero_orientation": {"roll": 0.5, "pitch": -0.3}
    }
  }
}
```

---

## Usage Examples

### Example 1: Read Sensor Data

```python
from sensor_manager import SensorManager

manager = SensorManager()
manager.add_sensor('A', 'Base', i2c_address=0x53)
manager.calibrate_joint('A')

# Read angle
feedback = manager.read_joint('A')
print(f"Joint A angle: {feedback.measured_angle:.1f}°")
```

### Example 2: Monitor All Joints

```python
from sensor_manager import setup_thor_sensors

manager = setup_thor_sensors(simulate=False)
manager.calibrate_all()

# Continuous monitoring
manager.start_monitoring(interval=0.1)
```

### Example 3: Commanded vs Measured

```python
from sensor_integration import create_integrated_system
from robot_controller import MovementType

system = create_integrated_system()

# Move robot
target = {'A': 45.0, 'B': 30.0}
system.robot.move_all_joints(target, MovementType.G1_LINEAR, feedrate=300)

# Wait for movement
time.sleep(2)

# Compare
comparison = system.sensors.compare_to_commanded(target)
for joint_id, comp in comparison.items():
    print(f"{joint_id}: Error = {comp['error']:.1f}°")
```

### Example 4: Closed-Loop Control

```python
system = create_integrated_system()

# Enable closed-loop
system.closed_loop_config.enabled = True
system.closed_loop_config.max_error = 2.0
system.start_closed_loop()

# Robot will automatically correct position errors
target = {'A': 45.0, 'B': 30.0, 'D': -20.0}
system.update_commanded_position(target)

# Monitor corrections
time.sleep(10)
system.stop_closed_loop()
```

### Example 5: Integration with 3D Viewer

```python
from viewer_3d import create_interactive_viewer
from sensor_integration import create_integrated_system

system = create_integrated_system()
viewer = create_interactive_viewer()

# Update viewer with actual position
def update_viewer():
    measured = system.sensors.get_joint_angles()
    viewer.update_arm(measured)

# Callback for sensor updates
system.on_position_updated = lambda angles: update_viewer()

# Start monitoring
system.start_closed_loop()
viewer.show()
```

---

## Troubleshooting

### Sensor Not Detected

**Problem:** `i2cdetect` doesn't show sensor address

**Solutions:**
- Check wiring (VCC, GND, SDA, SCL)
- Verify I2C is enabled
- Try different I2C bus (`-y 0` instead of `-y 1`)
- Check sensor power LED
- Measure voltage at VCC pin (should be 3.3V)

### Wrong Device ID

**Problem:** Device ID is not 0xE5

**Solutions:**
- May be a clone or different sensor
- Check sensor datasheet
- Verify it's actually an ADXL345

### Unstable Readings

**Problem:** Readings jump around erratically

**Solutions:**
- Secure sensor mounting (no vibration)
- Add delay between readings
- Increase averaging samples
- Check for loose wires
- Reduce data rate
- Add pull-up resistors (2.2kΩ to 3.3V) on SDA/SCL

### Incorrect Angles

**Problem:** Measured angles don't match actual position

**Solutions:**
- Re-calibrate sensor
- Check sensor mounting orientation
- Verify joint is at true 0° during calibration
- Check axis mapping configuration
- Consider sensor axis alignment

### I2C Communication Errors

**Problem:** Random I2C timeouts or errors

**Solutions:**
- Shorten wire lengths
- Add pull-up resistors
- Reduce I2C clock speed
- Check for electromagnetic interference
- Use shielded cables
- Add decoupling capacitors (0.1µF) near sensors

### Address Conflicts

**Problem:** Multiple sensors with same address

**Solutions:**
- Change SDO pin connection (GND vs VCC)
- Use I2C multiplexer
- Use different I2C buses
- Verify addresses with `i2cdetect`

---

## Advanced Topics

### Using I2C Multiplexer

For more than 2 sensors on one bus:

```python
# TCA9548A multiplexer example
class MultiplexedSensor:
    def __init__(self, mux_channel, sensor_address):
        self.mux = smbus2.SMBus(1)
        self.mux_address = 0x70  # TCA9548A default
        self.channel = mux_channel
        self.sensor = ADXL345(address=sensor_address)

    def select_channel(self):
        self.mux.write_byte(self.mux_address, 1 << self.channel)

    def read(self):
        self.select_channel()
        return self.sensor.read()
```

### Custom Axis Mapping

If sensor is mounted in non-standard orientation:

```python
config = JointSensorConfig(
    joint_id='A',
    joint_name='Base',
    i2c_address=0x53,
    axis_mapping={'primary': 'pitch', 'secondary': 'roll'},  # Swapped
    zero_orientation={'roll': 0.0, 'pitch': 0.0}
)
```

### Data Logging

Record sensor data for analysis:

```python
import csv
from datetime import datetime

with open('sensor_log.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['Timestamp', 'Joint', 'Angle', 'Accel_X', 'Accel_Y', 'Accel_Z'])

    while True:
        feedback = manager.read_all()
        for joint_id, fb in feedback.items():
            writer.writerow([
                datetime.now().isoformat(),
                joint_id,
                fb.measured_angle,
                fb.acceleration.x,
                fb.acceleration.y,
                fb.acceleration.z
            ])
        time.sleep(0.1)
```

---

## Safety Considerations

1. **Power** - Use 3.3V, NOT 5V (will damage sensor)
2. **Wiring** - Secure all connections to prevent shorts
3. **Mounting** - Ensure sensors don't interfere with movement
4. **Testing** - Test with slow movements first
5. **Limits** - Respect joint angle limits
6. **Monitoring** - Watch for excessive position errors

---

## Reference

### ADXL345 Specifications

- **Measurement Range:** ±2g, ±4g, ±8g, ±16g (software selectable)
- **Resolution:** 10-bit to 13-bit
- **Data Rate:** 0.1 Hz to 3200 Hz
- **Power:** 2.0V to 3.6V
- **Interface:** I2C (up to 400 kHz) or SPI (up to 5 MHz)

### Useful Resources

- [ADXL345 Datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/ADXL345.pdf)
- [I2C Protocol](https://www.i2c-bus.org/)
- [smbus2 Documentation](https://pypi.org/project/smbus2/)

---

## Support

For issues or questions:
1. Check this guide's troubleshooting section
2. Run example scripts to verify setup
3. Test individual sensors with `python adxl345_sensor.py`
4. Check GitHub issues for similar problems

**Happy sensing!** 🤖📡
