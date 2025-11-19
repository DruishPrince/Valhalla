@echo off
REM Quick fix for Python 3.14 compatibility
REM Installs minimal working packages

echo ============================================================
echo Quick Fix - Minimal Installation
echo ============================================================
echo.

echo Your Python 3.14 is too new for full installation.
echo This script installs minimal packages that DO work.
echo.
echo For full features, please install Python 3.11:
echo   https://www.python.org/downloads/release/python-3119/
echo.
echo ============================================================
echo.

pause

REM Activate venv if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
    echo.
)

echo Installing minimal packages...
echo.

echo [1/3] Installing PyQt5 (works with Python 3.14)...
pip install PyQt5
echo.

echo [2/3] Installing pyserial...
pip install pyserial
echo.

echo [3/3] Trying numpy pre-release...
pip install --pre numpy
if errorlevel 1 (
    echo NumPy failed - full GUI won't work
    echo But minimal GUI should work!
)
echo.

echo ============================================================
echo Testing what works...
echo ============================================================
echo.

python -c "import PyQt5; print('✓ PyQt5 works')" 2>nul && (
    python -c "import serial; print('✓ pyserial works')" 2>nul && (
        echo.
        echo ✓✓✓ Minimal packages installed! ✓✓✓
        echo.
        echo You can now run:
        echo   python asgard_minimal.py
        echo.
        echo This gives you basic robot control.
        echo.
        echo For FULL features with Kinect and all advanced features:
        echo   - Install Python 3.11.9
        echo   - See: PYTHON_VERSION_FIX.md
        echo.
    )
)

python -c "import cv2" 2>nul || (
    echo.
    echo ✗ OpenCV not available - Kinect features won't work
    echo ✗ This is expected with Python 3.14
    echo.
)

python -c "import numpy" 2>nul || (
    echo.
    echo ✗ NumPy not available - 3D features won't work
    echo ✗ This is expected with Python 3.14
    echo.
)

echo ============================================================

pause
