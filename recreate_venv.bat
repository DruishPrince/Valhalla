@echo off
REM ========================================
REM Recreate Virtual Environment - Complete Reset
REM ========================================

echo ========================================
echo Virtual Environment Recreation Script
echo ========================================
echo.
echo WARNING: This will DELETE your existing virtual environment
echo          and create a fresh one with all dependencies.
echo.

set /p confirm="Are you sure you want to continue? (yes/no): "
if /i not "%confirm%"=="yes" (
    echo Cancelled.
    pause
    exit /b 0
)

echo.
echo Step 1: Deactivating current virtual environment...
echo ========================================

call deactivate 2>nul

echo.
echo Step 2: Removing old virtual environment...
echo ========================================

if exist "venv\" (
    echo Deleting venv folder...
    rmdir /s /q venv
    echo Done!
) else (
    echo No existing venv found.
)

echo.
echo Step 3: Checking Python installation...
echo ========================================

python --version
if errorlevel 1 (
    echo ERROR: Python not found in PATH!
    echo Please install Python 3.7+ and add it to your PATH.
    pause
    exit /b 1
)

echo.
echo Step 4: Creating new virtual environment...
echo ========================================

python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment!
    pause
    exit /b 1
)

echo.
echo Step 5: Activating virtual environment...
echo ========================================

call venv\Scripts\activate.bat

echo.
echo Step 6: Upgrading pip...
echo ========================================

python -m pip install --upgrade pip

echo.
echo Step 7: Installing dependencies...
echo ========================================
echo.

echo Installing PyQt5...
pip install PyQt5

echo.
echo Installing pyserial...
pip install pyserial

echo.
echo Installing numpy (compatible version)...
pip install numpy==1.24.3

echo.
echo Installing opencv-python...
pip install opencv-python

echo.
echo Installing matplotlib...
pip install matplotlib

echo.
echo Installing scipy...
pip install scipy

echo.
echo Installing pygame (for Xbox controller)...
echo Note: Using pre-built wheel to avoid build issues on Python 3.12+
pip install pygame --only-binary :all:
if errorlevel 1 (
    echo Trying specific version...
    pip install pygame==2.5.2
)
if errorlevel 1 (
    echo Trying pygame-ce as fallback...
    pip install pygame-ce
)

echo.
echo Step 8: Verifying installation...
echo ========================================
echo.

python -c "import PyQt5; print('[OK] PyQt5 version:', PyQt5.QtCore.QT_VERSION_STR)"
python -c "import serial; print('[OK] pyserial imported')"
python -c "import numpy; print('[OK] Numpy version:', numpy.__version__)"
python -c "import cv2; print('[OK] OpenCV version:', cv2.__version__)"
python -c "import matplotlib; print('[OK] Matplotlib version:', matplotlib.__version__)"
python -c "import scipy; print('[OK] Scipy version:', scipy.__version__)"
python -c "import pygame; print('[OK] Pygame version:', pygame.__version__)"

echo.
echo ========================================
echo Virtual environment recreated successfully!
echo ========================================
echo.
echo Installed packages:
pip list
echo.
echo You can now run your application!
echo.

pause
