# Troubleshooting Guide - Asgard Enhanced

Quick solutions for common problems when running Asgard Enhanced GUI.

## Quick Fix Steps

### Step 1: Run Setup Script (Recommended)

```cmd
setup_windows.bat
```

This installs all required dependencies automatically.

### Step 2: Test Installation

```cmd
venv\Scripts\activate
python test_installation.py
```

This checks what's installed and what's missing.

### Step 3: Try Simple Launcher

```cmd
run_simple.bat
```

This runs tests first, then asks before launching.

### Step 4: Try Minimal Version

If full version doesn't work:

```cmd
venv\Scripts\activate
python asgard_minimal.py
```

This only requires PyQt5 and pyserial.

---

## Common Error Messages

### Error: "No module named 'PyQt5'"

**Cause:** PyQt5 not installed

**Fix:**
```cmd
venv\Scripts\activate
pip install PyQt5
```

---

### Error: "No module named 'cv2'"

**Cause:** OpenCV not installed

**Fix:**
```cmd
venv\Scripts\activate
pip install opencv-python
```

---

### Error: "No module named 'serial'"

**Cause:** pyserial not installed

**Fix:**
```cmd
venv\Scripts\activate
pip install pyserial
```

---

### Error: "Virtual environment not found"

**Cause:** venv folder doesn't exist

**Fix:**
```cmd
python -m venv venv
setup_windows.bat
```

---

### Error: "python is not recognized"

**Cause:** Python not in PATH

**Fix:**
1. Reinstall Python from python.org
2. During installation, check "Add Python to PATH"
3. OR manually add Python to PATH:
   - Search Windows for "Environment Variables"
   - Edit "Path" variable
   - Add: `C:\Users\YourName\AppData\Local\Programs\Python\Python311`

---

### Error: Program starts but window doesn't appear

**Possible causes:**
1. Window opened off-screen
2. Graphics driver issue
3. Multiple monitors

**Fix:**
- Press Alt+Space, then M (Move), then arrow keys
- Update graphics drivers
- Try on single monitor

---

### Error: "ImportError" for project modules

**Example:** `No module named 'robot_controller'`

**Cause:** Running from wrong directory

**Fix:**
```cmd
cd C:\Users\YourName\Documents\Valhalla
run_asgard_enhanced.bat
```

Make sure you're in the project directory!

---

## Step-by-Step Manual Setup

If automated setup fails, do this manually:

### 1. Check Python

```cmd
python --version
```

Should show Python 3.8 or newer.

### 2. Create Virtual Environment

```cmd
cd C:\Users\YourName\Documents\Valhalla
python -m venv venv
```

### 3. Activate Virtual Environment

```cmd
venv\Scripts\activate
```

Your prompt should show `(venv)` at the start.

### 4. Upgrade pip

```cmd
python -m pip install --upgrade pip
```

### 5. Install Core Dependencies

```cmd
pip install PyQt5
pip install pyserial
pip install opencv-python
pip install numpy
pip install matplotlib
pip install scipy
```

### 6. Test Installation

```cmd
python test_installation.py
```

Should show all checkmarks (✓).

### 7. Run GUI

```cmd
python asgard_enhanced.py
```

---

## Specific Module Issues

### Kinect Support

**If you don't have a Kinect**, you can skip Kinect installation.

The GUI will work fine without it - Kinect features just won't be available.

**If you do have a Kinect:**

For **Kinect v1** (Xbox 360):
```cmd
pip install freenect
```

For **Kinect v2** (Xbox One):
1. Download libfreenect2 from: https://github.com/OpenKinect/libfreenect2
2. Follow Windows installation instructions
3. Then: `pip install pylibfreenect2`

For **Azure Kinect**:
1. Download Azure Kinect SDK from: https://github.com/microsoft/Azure-Kinect-Sensor-SDK
2. Install the SDK
3. Then: `pip install pyk4a`

### Sensor Support (ADXL345)

**Only needed if:**
- Using FLY Super ♾️ Pro board
- Have ADXL345 sensors
- Using Pi Zero 2W or Pico gateway

**Skip if** you don't have sensors.

To install:
```cmd
pip install smbus2
```

---

## Command Line Testing

Test if modules import correctly:

```cmd
venv\Scripts\activate

python -c "import PyQt5; print('PyQt5 OK')"
python -c "import serial; print('pyserial OK')"
python -c "import cv2; print('OpenCV OK')"
python -c "import numpy; print('NumPy OK')"
python -c "import matplotlib; print('Matplotlib OK')"
python -c "import scipy; print('SciPy OK')"
```

Each should print "OK" with no errors.

---

## Still Not Working?

### Option 1: Use Minimal Version

```cmd
python asgard_minimal.py
```

This is a simplified GUI that only needs PyQt5 and pyserial.

### Option 2: Check Logs

Look for error messages when running:

```cmd
python asgard_enhanced.py > output.log 2>&1
```

Then check `output.log` for detailed errors.

### Option 3: Fresh Start

Delete and recreate everything:

```cmd
rmdir /s venv
python -m venv venv
venv\Scripts\activate
pip install PyQt5 pyserial opencv-python numpy matplotlib scipy
python asgard_enhanced.py
```

---

## Getting Help

### Information to Provide

If asking for help, include:

1. **Python version:**
   ```cmd
   python --version
   ```

2. **Operating System:**
   - Windows 10 / Windows 11

3. **Error message:**
   - Full text of error
   - Or screenshot

4. **What you tried:**
   - Did you run setup_windows.bat?
   - Did test_installation.py pass?

### Example Help Request

```
I'm getting "No module named 'PyQt5'" error.

Python version: 3.11.0
OS: Windows 11
What I tried:
- Ran setup_windows.bat - completed successfully
- Ran test_installation.py - showed PyQt5 as missing
- Ran "pip install PyQt5" manually - seemed to install
- Still getting the error

Error message when running asgard_enhanced.py:
[paste full error here]
```

---

## Verification Checklist

Before asking for help, verify:

- [ ] Python 3.8+ is installed
- [ ] Running from correct directory (Valhalla folder)
- [ ] Virtual environment exists (`venv` folder present)
- [ ] Virtual environment is activated (prompt shows `(venv)`)
- [ ] Ran `setup_windows.bat` successfully
- [ ] `test_installation.py` shows core modules as OK
- [ ] `asgard_enhanced.py` file exists in current directory
- [ ] No typos in commands

---

## Alternative: Run Without Virtual Environment

If virtual environment causes issues:

```cmd
# Install globally (not recommended but works)
pip install PyQt5 pyserial opencv-python numpy matplotlib scipy

# Run directly
python asgard_enhanced.py
```

**Note:** This installs packages system-wide, which can cause conflicts.
Virtual environment is recommended.

---

## Linux/Mac Users

If on Linux or Mac:

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install PyQt5 pyserial opencv-python numpy matplotlib scipy

# Run
python3 asgard_enhanced.py

# Or use script
chmod +x run_asgard_enhanced.sh
./run_asgard_enhanced.sh
```

---

## Success Criteria

You'll know it's working when:

1. `test_installation.py` shows all ✓ (checkmarks)
2. `python asgard_enhanced.py` opens a window with 5 tabs:
   - Robot Control
   - Kinect Vision
   - Sensors
   - Action Sequencer
   - Configuration

If you see the window, it's working! 🎉

---

**Still stuck? The minimal version (`asgard_minimal.py`) always works with just PyQt5 installed.**
