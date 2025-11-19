@echo off
REM Setup script for Asgard Enhanced
REM Run this once to set up everything

echo ============================================================
echo Asgard Enhanced - Setup and Installation
echo ============================================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8 or newer from python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo [1/5] Python found:
python --version
echo.

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [2/5] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
) else (
    echo [2/5] Virtual environment already exists
)
echo.

REM Activate virtual environment
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo.

REM Upgrade pip
echo [4/5] Upgrading pip...
python -m pip install --upgrade pip
echo.

REM Install requirements
echo [5/5] Installing required packages...
echo This may take several minutes...
echo.

REM Install core requirements
echo Installing PyQt5...
pip install PyQt5>=5.15.0
if errorlevel 1 (
    echo WARNING: PyQt5 installation failed
)

echo Installing pyserial...
pip install pyserial>=3.5

echo Installing OpenCV...
pip install opencv-python>=4.5.0

echo Installing NumPy...
pip install numpy>=1.21.0

echo Installing Matplotlib...
pip install matplotlib>=3.3.0

echo Installing SciPy...
pip install scipy>=1.7.0

echo.
echo ============================================================
echo Installation Complete!
echo ============================================================
echo.
echo Optional: Install Kinect support (choose one based on your camera):
echo   For Kinect v1:    pip install freenect
echo   For Kinect v2:    pip install pylibfreenect2
echo   For Azure Kinect: pip install pyk4a
echo.
echo Optional: Install sensor support (if using ADXL345):
echo   pip install smbus2
echo.
echo To run Asgard Enhanced:
echo   run_asgard_enhanced.bat
echo.

deactivate
pause
