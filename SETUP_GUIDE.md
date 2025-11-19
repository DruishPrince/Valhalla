# Complete System Setup Guide

Step-by-step instructions for setting up the Thor robotic arm control system on Windows with Raspberry Pi Zero 2W sensor gateway.

## Table of Contents
1. [System Overview](#system-overview)
2. [Windows Main Computer Setup](#windows-main-computer-setup)
3. [Raspberry Pi Zero 2W Sensor Gateway Setup](#raspberry-pi-zero-2w-sensor-gateway-setup)
4. [Hardware Connections](#hardware-connections)
5. [Testing and Verification](#testing-and-verification)
6. [Troubleshooting](#troubleshooting)

---

## System Overview

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Windows PC (Main Computer)             │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ Robot Control  │  │ 3D Vision    │  │ Gateway     │ │
│  │ (Python)       │  │ (Kinect)     │  │ Client      │ │
│  └───────┬────────┘  └──────┬───────┘  └──────┬──────┘ │
└──────────┼────────────────────┼──────────────────┼────────┘
           │                    │                  │
      USB Serial          USB (Kinect)        USB Serial
           │                    │                  │
  ┌────────▼────────┐   ┌───────▼──────┐   ┌─────▼────────────┐
  │ FLY Super 8 Pro │   │    Kinect    │   │  Pi Zero 2W      │
  │ (Robot Board)   │   │    Camera    │   │  (Sensor Gateway)│
  │  /dev/ttyUSB0   │   │              │   │  /dev/ttyUSB1    │
  └─────────────────┘   └──────────────┘   └────────┬─────────┘
                                                     │
                                                   I2C Bus
                                                     │
                        ┌────────────────────────────┼─────────┐
                        │                            │         │
                  ┌─────▼─────┐              ┌───────▼──────┐ │
                  │ ADXL345   │              │  ADXL345     │ │
                  │ Sensor 1  │              │  Sensor 2    │ │
                  │ (Joint A) │              │  (Joint B)   │ │
                  └───────────┘              └──────────────┘ │
```

### What You'll Need

#### Hardware
- **Windows PC** (Windows 10/11, 8GB+ RAM recommended)
- **Thor Robotic Arm** with FLY Super ♾️ Pro controller board
- **Kinect Camera** (v1, v2, or Azure Kinect - optional but recommended)
- **Raspberry Pi Zero 2W** with microSD card (8GB+)
- **ADXL345 Sensors** (3-6 sensors, one per moving joint)
- **USB Cables**:
  - USB cable for FLY board
  - USB cable for Kinect
  - Micro USB cable for Pi Zero 2W
- **Power Supply** for Kinect (if using v1)
- **Jumper Wires** for I2C connections

#### Software
- Python 3.8 or newer
- Git for Windows
- Raspberry Pi OS Lite
- Various Python libraries (detailed below)

---

## Windows Main Computer Setup

### Step 1: Install Python

1. Download Python 3.11 from [python.org](https://www.python.org/downloads/)
2. Run installer
3. **IMPORTANT**: Check "Add Python to PATH"
4. Click "Install Now"
5. Verify installation:
   ```cmd
   python --version
   pip --version
   ```

### Step 2: Install Git

1. Download Git from [git-scm.com](https://git-scm.com/download/win)
2. Run installer with default settings
3. Verify:
   ```cmd
   git --version
   ```

### Step 3: Clone Repository

```cmd
# Open Command Prompt or PowerShell
cd C:\Users\YourUsername\Documents
git clone https://github.com/YourUsername/Valhalla.git
cd Valhalla
```

### Step 4: Create Virtual Environment

```cmd
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate

# Your prompt should now show (venv)
```

### Step 5: Install Core Dependencies

```cmd
# Upgrade pip
python -m pip install --upgrade pip

# Install core requirements
pip install PyQt5>=5.15.0
pip install pyserial>=3.5
pip install opencv-python>=4.5.0
pip install opencv-contrib-python>=4.5.0
pip install numpy>=1.21.0
pip install matplotlib>=3.3.0
pip install scipy>=1.7.0
```

### Step 6: Install Kinect Support (Optional)

Choose ONE based on your Kinect model:

#### For Kinect v1 (Xbox 360)

```cmd
# Download and install libfreenect for Windows
# Visit: https://github.com/OpenKinect/libfreenect/releases
# Download and run the Windows installer

# Then install Python bindings
pip install freenect
```

**Alternative (if pip fails):**
```cmd
# Download pre-built wheel from:
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#freenect
# Then install:
pip install freenect‑1.0.0‑cp311‑cp311‑win_amd64.whl
```

#### For Kinect v2 (Xbox One)

```cmd
# Install libfreenect2
# This is more complex on Windows, follow:
# https://github.com/OpenKinect/libfreenect2#windows

# Then install Python bindings
pip install pylibfreenect2
```

#### For Azure Kinect

```cmd
# Install Azure Kinect SDK
# Download from: https://github.com/microsoft/Azure-Kinect-Sensor-SDK/releases
# Run the installer (e.g., Azure Kinect SDK 1.4.1.exe)

# Install Python bindings
pip install pyk4a
```

### Step 7: Install USB Serial Drivers

1. **Download USB Drivers**:
   - For CH340/CH341 chips: [CH341SER.EXE](http://www.wch-ic.com/downloads/CH341SER_EXE.html)
   - For FTDI chips: [FTDI VCP Driver](https://ftdichip.com/drivers/vcp-drivers/)

2. **Install drivers**:
   - Run the downloaded installer
   - Restart computer if prompted

3. **Connect FLY board** via USB

4. **Find COM port**:
   - Open Device Manager (Win + X → Device Manager)
   - Expand "Ports (COM & LPT)"
   - Note the COM port (e.g., COM3, COM4)

### Step 8: Configure System

```cmd
# Still in the Valhalla directory with venv activated

# Copy the default config
python -c "from config_manager import ConfigManager; ConfigManager()"

# This creates asgard_config.json
```

Edit `asgard_config.json`:

```json
{
  "serial": {
    "port": "COM3",  // Change to your COM port
    "baudrate": 115200
  },
  "boards": {
    "current_board": "fly_super_8_pro"  // or "generic"
  },
  "kinect": {
    "enabled": true,  // If you have Kinect
    "version": "auto"  // Will auto-detect
  },
  "sensors": {
    "enabled": true,  // If using ADXL345 sensors
    "mode": "gateway"  // Using Pi Zero 2W gateway
  },
  "sensor_gateway": {
    "connection_mode": "serial",
    "serial_port": "COM4"  // Will be different from robot port
  }
}
```

### Step 9: Test Basic Setup

```cmd
# Test robot connection
python -c "
from robot_controller import RobotController
robot = RobotController()
if robot.connect('COM3', 115200):
    print('✓ Robot connected!')
    robot.disconnect()
else:
    print('✗ Connection failed')
"
```

### Step 10: Create Desktop Shortcuts (Optional)

Create `run_robot_control.bat`:
```batch
@echo off
cd C:\Users\YourUsername\Documents\Valhalla
call venv\Scripts\activate
python Asgard.py
pause
```

Right-click → Create shortcut → Move to Desktop

---

## Raspberry Pi Zero 2W Sensor Gateway Setup

### Step 1: Prepare microSD Card

1. **Download Raspberry Pi Imager**:
   - Visit [raspberrypi.com/software](https://www.raspberrypi.com/software/)
   - Download and install for Windows

2. **Flash Raspberry Pi OS**:
   - Insert microSD card into PC
   - Open Raspberry Pi Imager
   - Choose OS: **Raspberry Pi OS Lite (64-bit)**
   - Choose Storage: Your microSD card
   - Click gear icon ⚙️ for advanced options:
     - ✓ Enable SSH
     - ✓ Set username: `pi`
     - ✓ Set password: (your choice)
     - ✓ Configure WiFi (optional)
     - ✓ Set locale settings
   - Click "WRITE"
   - Wait for completion

3. **Eject microSD card** and insert into Pi Zero 2W

### Step 2: First Boot and Connection

#### Option A: WiFi Connection (Recommended)

1. Power on Pi Zero 2W (via micro USB)
2. Wait 2-3 minutes for first boot
3. Find Pi's IP address:
   ```cmd
   # On Windows, use Advanced IP Scanner or
   ping raspberrypi.local
   ```
4. Connect via SSH:
   ```cmd
   # Download PuTTY from putty.org
   # Or use Windows built-in SSH:
   ssh pi@raspberrypi.local
   # Enter password when prompted
   ```

#### Option B: USB Connection

1. Connect Pi Zero 2W to PC via micro USB (data port, not power)
2. Wait for driver installation
3. Connect:
   ```cmd
   ssh pi@raspberrypi.local
   ```

### Step 3: Initial Pi Configuration

```bash
# SSH into Pi
ssh pi@raspberrypi.local

# Update system
sudo apt update && sudo apt upgrade -y

# This may take 10-15 minutes on first run
```

### Step 4: Enable I2C

```bash
# Run configuration tool
sudo raspi-config

# Navigate to:
# 3. Interface Options
# → I2C
# → Yes (Enable I2C)
# → OK
# → Finish

# Reboot
sudo reboot
```

Wait 1 minute, then reconnect:
```cmd
ssh pi@raspberrypi.local
```

### Step 5: Install I2C Tools

```bash
# Install I2C utilities
sudo apt install -y python3-pip python3-smbus i2c-tools

# Test I2C (without sensors connected, should show empty)
sudo i2cdetect -y 1
```

### Step 6: Install Python Dependencies

```bash
# Install required libraries
pip3 install smbus2 pyserial numpy

# Verify installation
python3 -c "import smbus2; import serial; import numpy; print('✓ All libraries installed')"
```

### Step 7: Transfer Gateway Script

From your **Windows PC**:

```cmd
# Navigate to Valhalla directory
cd C:\Users\YourUsername\Documents\Valhalla

# Copy script to Pi (replace with your Pi's IP or use raspberrypi.local)
# Using SCP (requires SSH/SCP client like PuTTY's pscp.exe)
pscp sensor_gateway_pi.py pi@raspberrypi.local:/home/pi/

# Or use WinSCP (GUI tool): https://winscp.net/
```

Alternatively, on the **Pi**:

```bash
# Create the file directly
nano /home/pi/sensor_gateway_pi.py

# Copy the contents from your Windows file
# Ctrl+X, Y, Enter to save
```

### Step 8: Configure Auto-Start (Optional)

```bash
# Create systemd service
sudo nano /etc/systemd/system/sensor-gateway.service
```

Add this content:
```ini
[Unit]
Description=ADXL345 Sensor Gateway
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
ExecStart=/usr/bin/python3 /home/pi/sensor_gateway_pi.py --serial /dev/ttyACM0 --baud 115200
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable sensor-gateway.service
sudo systemctl start sensor-gateway.service

# Check status
sudo systemctl status sensor-gateway.service
```

### Step 9: Test Sensor Detection

With ADXL345 sensors connected:

```bash
# Scan for I2C devices
sudo i2cdetect -y 1

# Should show:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 00:          -- -- -- -- -- -- -- -- -- -- -- -- --
# 10: -- -- -- -- -- -- -- -- -- -- -- -- -- 1d -- --
# 20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 50: -- -- -- 53 -- -- -- -- -- -- -- -- -- -- -- --
# 60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 70: -- -- -- -- -- -- -- --

# 0x53 and 0x1D are ADXL345 sensors
```

Test the gateway script:
```bash
python3 /home/pi/sensor_gateway_pi.py --serial /dev/ttyACM0 --baud 115200

# Should start streaming JSON sensor data
# Press Ctrl+C to stop
```

---

## Hardware Connections

### ADXL345 Sensors to Pi Zero 2W

**Wiring for 2 sensors (most common):**

```
Raspberry Pi Zero 2W          ADXL345 Sensors
┌────────────────────┐
│ PIN 1  (3.3V) ─────┼───┬─── Sensor 1 VCC (Address 0x53)
│ PIN 6  (GND)  ─────┼───┼─── Sensor 1 GND
│ PIN 3  (SDA)  ─────┼───┼─── Sensor 1 SDA
│ PIN 5  (SCL)  ─────┼───┼─── Sensor 1 SCL
│                    │   │    Sensor 1 SDO ─── GND
│                    │   │
│                    │   ├─── Sensor 2 VCC (Address 0x1D)
│                    │   ├─── Sensor 2 GND
│                    │   ├─── Sensor 2 SDA
│                    │   ├─── Sensor 2 SCL
│                    │   │    Sensor 2 SDO ─── 3.3V
└────────────────────┘   │
```

**Pin Reference:**
| Pi Pin | Function | Wire Color (Suggested) |
|--------|----------|------------------------|
| Pin 1  | 3.3V     | Red                    |
| Pin 3  | SDA      | Green                  |
| Pin 5  | SCL      | Yellow                 |
| Pin 6  | GND      | Black                  |

### USB Connections

**Windows PC USB Ports:**
1. **COM3** (or similar): FLY Super ♾️ Pro board
2. **COM4** (or similar): Pi Zero 2W (when connected via USB)
3. **USB 3.0**: Kinect camera

### Physical Sensor Mounting

Mount ADXL345 sensors on each moving joint:
- **Joint A (Base)**: Sensor on rotating base
- **Joint B (Shoulder)**: Sensor on shoulder link
- **Joint D (Elbow)**: Sensor on elbow link
- Align sensor so gravity provides meaningful angle data

---

## Testing and Verification

### Test 1: Robot Communication

On **Windows**:
```cmd
cd C:\Users\YourUsername\Documents\Valhalla
venv\Scripts\activate
python

>>> from robot_controller import RobotController
>>> robot = RobotController()
>>> robot.connect('COM3', 115200)  # Use your COM port
>>> robot.send_command('?')  # Query status
>>> robot.disconnect()
>>> exit()
```

### Test 2: Sensor Gateway

On **Windows**, with Pi Zero 2W connected via USB:

```cmd
python

>>> from sensor_gateway_client import SensorGatewayClient, GatewayConfig
>>> config = GatewayConfig(mode='serial', serial_port='COM4')
>>> client = SensorGatewayClient(config)
>>> client.connect()
>>> import time; time.sleep(2)
>>> status = client.get_status()
>>> print(status)
>>> client.disconnect()
>>> exit()
```

### Test 3: Kinect Camera

```cmd
python kinect_interface.py
```

You should see:
- Kinect version detected
- RGB and depth windows
- Press 'q' to quit

### Test 4: Complete Integration

```cmd
python example_fly_board_setup.py
```

Follow the interactive menu to test:
1. Sensor calibration
2. Basic movement with feedback
3. Closed-loop control

### Test 5: Kinect Manipulation

```cmd
python example_kinect_manipulation.py
```

Try the examples:
1. Accurate pick and place
2. Obstacle avoidance
3. Volume measurement

---

## Troubleshooting

### Windows Issues

#### Python not recognized
```cmd
# Add Python to PATH manually:
# 1. Search "Environment Variables"
# 2. Edit "Path" variable
# 3. Add: C:\Users\YourUsername\AppData\Local\Programs\Python\Python311
# 4. Add: C:\Users\YourUsername\AppData\Local\Programs\Python\Python311\Scripts
```

#### COM Port Access Denied
- Close any other programs using the port
- Check Device Manager for port conflicts
- Try a different USB port
- Reinstall USB drivers

#### Module Not Found Errors
```cmd
# Make sure virtual environment is activated
venv\Scripts\activate

# Reinstall the missing module
pip install <module-name>
```

### Pi Zero 2W Issues

#### Cannot SSH to Pi
```bash
# On Windows, try:
ping raspberrypi.local

# If that fails:
# 1. Check WiFi credentials in Raspberry Pi Imager
# 2. Try USB connection instead
# 3. Connect monitor/keyboard directly to Pi
```

#### I2C Not Working
```bash
# Check if I2C is enabled
ls /dev/i2c-*

# Should show: /dev/i2c-1

# If not:
sudo raspi-config
# Interface Options → I2C → Enable
sudo reboot
```

#### Sensors Not Detected
```bash
# Check wiring connections
# Verify power (3.3V, NOT 5V)
# Test with multimeter if available

# Check I2C bus
sudo i2cdetect -y 1

# If still nothing, try the other I2C bus
sudo i2cdetect -y 0
```

#### Gateway Not Streaming Data
```bash
# Check if script is running
ps aux | grep sensor_gateway

# View logs
sudo journalctl -u sensor-gateway.service -f

# Test manually
python3 /home/pi/sensor_gateway_pi.py --serial /dev/ttyACM0
```

### Kinect Issues

#### Kinect Not Detected (Windows)
- Install correct USB drivers for your Kinect model
- Try different USB ports (USB 3.0 for v2/Azure)
- Check Windows Device Manager for errors
- Ensure Kinect is powered (v1 needs external 12V)

#### Poor Depth Quality
- Avoid direct sunlight
- Keep within optimal range (0.5m - 3m)
- Clean Kinect IR sensor
- Avoid reflective surfaces

---

## Quick Reference Commands

### Windows

```cmd
# Activate environment
cd C:\Users\YourUsername\Documents\Valhalla
venv\Scripts\activate

# Run main GUI
python Asgard.py

# Run 3D control
python robot_3d_control.py

# Run Kinect examples
python example_kinect_manipulation.py

# Run FLY board setup
python example_fly_board_setup.py
```

### Raspberry Pi Zero 2W

```bash
# SSH to Pi
ssh pi@raspberrypi.local

# Scan I2C
sudo i2cdetect -y 1

# Test gateway
python3 /home/pi/sensor_gateway_pi.py --serial /dev/ttyACM0

# View gateway logs
sudo journalctl -u sensor-gateway.service -f

# Restart gateway service
sudo systemctl restart sensor-gateway.service

# Stop gateway service
sudo systemctl stop sensor-gateway.service
```

---

## Next Steps

After successful setup:

1. **Calibrate Camera** (if using vision):
   ```cmd
   python calibrate_camera.py
   ```

2. **Calibrate Sensors** (if using ADXL345):
   ```cmd
   python calibrate_sensors.py
   ```

3. **Test 3D Control**:
   ```cmd
   python robot_3d_control.py
   ```

4. **Explore Examples**:
   - `examples.py` - Basic robot control
   - `example_3d_control.py` - 3D visualization
   - `example_sensor_feedback.py` - Sensor integration
   - `example_kinect_manipulation.py` - Kinect depth sensing

5. **Read Documentation**:
   - `README.md` - Overview
   - `SENSOR_GUIDE.md` - ADXL345 setup details
   - `KINECT_GUIDE.md` - Kinect setup details

---

**✓ You're now ready to use the complete Thor robotic arm system!**

For additional help, see troubleshooting sections or check the documentation files.
