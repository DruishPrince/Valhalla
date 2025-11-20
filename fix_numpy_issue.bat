@echo off
REM ========================================
REM Fix Numpy Import Error - Asgard/Thor
REM ========================================

echo ========================================
echo Numpy Import Error Fix Script
echo ========================================
echo.

REM Check if we're in the right directory
if not exist "asgard.py" (
    echo ERROR: asgard.py not found!
    echo Please run this script from the Valhalla directory.
    pause
    exit /b 1
)

echo Step 1: Checking for conflicting files...
echo ========================================

REM Check for numpy.py file conflict
if exist "numpy.py" (
    echo WARNING: Found conflicting numpy.py file!
    echo Renaming it to numpy.py.backup
    ren numpy.py numpy.py.backup
)

REM Check for numpy folder conflict
if exist "numpy\" (
    echo WARNING: Found conflicting numpy folder!
    echo Renaming it to numpy_backup
    ren numpy numpy_backup
)

REM Check for cv2.py file conflict
if exist "cv2.py" (
    echo WARNING: Found conflicting cv2.py file!
    echo Renaming it to cv2.py.backup
    ren cv2.py cv2.py.backup
)

echo.
echo Step 2: Activating virtual environment...
echo ========================================

if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run setup_windows.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo.
echo Step 3: Uninstalling problematic packages...
echo ========================================

pip uninstall numpy -y
pip uninstall opencv-python -y
pip uninstall opencv-contrib-python -y

echo.
echo Step 4: Clearing pip cache...
echo ========================================

pip cache purge

echo.
echo Step 5: Reinstalling numpy (compatible version)...
echo ========================================

pip install numpy==1.24.3

echo.
echo Step 6: Reinstalling opencv-python...
echo ========================================

pip install opencv-python

echo.
echo Step 7: Installing other dependencies...
echo ========================================

pip install matplotlib scipy pygame

echo.
echo Step 8: Testing numpy installation...
echo ========================================

python -c "import numpy; print('SUCCESS: Numpy version:', numpy.__version__)"
if errorlevel 1 (
    echo ERROR: Numpy test failed!
    pause
    exit /b 1
)

echo.
python -c "import cv2; print('SUCCESS: OpenCV version:', cv2.__version__)"
if errorlevel 1 (
    echo ERROR: OpenCV test failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Fix completed successfully!
echo ========================================
echo.
echo You can now run asgard_enhanced.py
echo.

pause
