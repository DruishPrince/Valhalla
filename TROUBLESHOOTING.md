# Troubleshooting Guide for Asgard

## Quick Fix Scripts

All scripts are designed to be run from the Valhalla directory on Windows.

### START_HERE.bat
**The main menu - start here if you're not sure what to do!**
- Interactive menu with all options
- Guides you through diagnostics and fixes

### For Numpy/OpenCV Import Errors

#### 1. diagnose_issue.bat
Run this first to identify the problem:
- Checks for conflicting files (numpy.py, cv2.py)
- Verifies virtual environment
- Tests all imports
- Shows detailed diagnostic information

#### 2. fix_numpy_issue.bat
Quick fix for numpy import errors:
- Removes conflicting files
- Reinstalls numpy with compatible version
- Reinstalls opencv-python
- Clears pip cache
- Tests installation

#### 3. recreate_venv.bat
Complete reset (use if quick fix doesn't work):
- Deletes entire virtual environment
- Creates fresh virtual environment
- Installs all dependencies
- Verifies installation

### Testing & Running

#### test_installation.bat
Verify all dependencies are working:
- Tests all 7 required packages
- Shows version numbers
- Indicates which packages failed (if any)

#### run_asgard.bat
Launch original Asgard with Xbox controller support:
- Activates virtual environment
- Runs asgard.py
- Shows helpful error messages

#### run_asgard_enhanced.bat
Launch enhanced version (if you have it):
- Includes additional features
- Same error handling

---

## Common Issues and Solutions

### Issue 1: "No module named 'numpy.core._multiarray_umath'"

**Cause:** Corrupted numpy installation or conflicting files

**Solution:**
```batch
1. Run diagnose_issue.bat
2. If it finds conflicts, run fix_numpy_issue.bat
3. If that doesn't work, run recreate_venv.bat
```

### Issue 2: "ImportError: Error importing numpy from its source directory"

**Cause:** There's a file or folder named `numpy` in your Valhalla directory

**Solution:**
```batch
1. Run diagnose_issue.bat (it will show the conflict)
2. Run fix_numpy_issue.bat (it will rename the conflicting file)
```

### Issue 3: Xbox Controller Not Detected

**Cause:** pygame not installed or controller not connected

**Solution:**
```batch
1. Make sure controller is connected via USB or Bluetooth
2. Activate virtual environment: venv\Scripts\activate
3. Install pygame: pip install pygame
4. Test: python -c "import pygame; pygame.init(); print(pygame.joystick.get_count())"
```

### Issue 4: Virtual Environment Not Found

**Solution:**
```batch
Run recreate_venv.bat
```

### Issue 5: Serial Port Connection Fails

**Cause:** Wrong COM port or permissions issue

**Solution:**
1. Check Device Manager for correct COM port
2. Make sure no other program is using the port
3. Try different baud rates (usually 115200)

---

## Manual Troubleshooting Steps

If scripts don't work, try these manual steps:

### Step 1: Check for Conflicting Files
```batch
cd C:\Thor-Robot-Arm\Angel-Thor\Valhalla
dir numpy*
dir cv2*
```
If you see `numpy.py` or `cv2.py`, rename or delete them.

### Step 2: Check Current Directory
```batch
cd
```
Make sure you're NOT inside a folder called "numpy" or "site-packages"

### Step 3: Reinstall Numpy Manually
```batch
venv\Scripts\activate
pip uninstall numpy -y
pip uninstall opencv-python -y
pip cache purge
pip install numpy==1.24.3
pip install opencv-python
```

### Step 4: Verify Installation
```batch
python -c "import numpy; print(numpy.__version__)"
python -c "import cv2; print(cv2.__version__)"
```

---

## Xbox Controller Setup

### Requirements
```batch
pip install pygame
```

### Verify Controller Connection
```batch
python -c "import pygame; pygame.init(); print('Joysticks:', pygame.joystick.get_count())"
```
Should show "Joysticks: 1" or higher

### Test Controller
```batch
python xbox_controller_test.py
```

---

## Recommended Fix Order

1. **First Time Setup:**
   ```batch
   recreate_venv.bat
   test_installation.bat
   run_asgard.bat
   ```

2. **Having Numpy Issues:**
   ```batch
   diagnose_issue.bat
   fix_numpy_issue.bat
   test_installation.bat
   ```

3. **Nothing Works:**
   ```batch
   recreate_venv.bat
   test_installation.bat
   ```

---

## Getting Help

If none of these solutions work:

1. Run `diagnose_issue.bat` and save the output
2. Run `test_installation.bat` and save the output
3. Note your Python version: `python --version`
4. Note your OS version
5. Share all this information when asking for help

---

## Additional Resources

- **README.md** - Full Xbox controller documentation
- **requirements.txt** - List of all dependencies
- **.gitignore** - Prevents committing cache files

---

## Quick Command Reference

```batch
# Activate virtual environment
venv\Scripts\activate

# Check Python version
python --version

# List installed packages
pip list

# Install single package
pip install package_name

# Install all requirements
pip install -r requirements.txt

# Test import
python -c "import package_name; print('OK')"

# Clear pip cache
pip cache purge

# Create new virtual environment
python -m venv venv
```
