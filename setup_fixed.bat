@echo off
REM Fixed setup script for Asgard Enhanced
REM Handles Python 3.14 compatibility issues

echo ============================================================
echo Asgard Enhanced - Fixed Setup
echo ============================================================
echo.

REM Check Python version
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo Checking Python version...
python --version
echo.

REM Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo Detected Python version: %PYVER%
echo.

REM Check if Python 3.14
echo %PYVER% | findstr /C:"3.14" >nul
if %errorlevel%==0 (
    echo ============================================================
    echo WARNING: Python 3.14 detected!
    echo ============================================================
    echo.
    echo Python 3.14 is too new. NumPy/OpenCV don't have pre-built wheels yet.
    echo.
    echo RECOMMENDED: Install Python 3.11 or 3.12 from python.org
    echo   - Download: https://www.python.org/downloads/
    echo   - Install Python 3.11.9 or 3.12.x
    echo   - Check "Add Python to PATH" during installation
    echo.
    echo After installing Python 3.11/3.12:
    echo   - Run: py -3.11 -m venv venv  (or py -3.12 -m venv venv)
    echo   - Then run this script again
    echo.
    set /p CONTINUE="Continue anyway with Python 3.14? (NOT RECOMMENDED) (y/n): "
    if /i not "%CONTINUE%"=="y" (
        echo.
        echo Setup cancelled. Please install Python 3.11 or 3.12.
        pause
        exit /b 1
    )
    echo.
    echo Continuing with Python 3.14... (may fail)
    echo.
)

REM Delete old venv if it exists
if exist "venv" (
    echo Found existing virtual environment
    set /p DELETE="Delete and recreate? (recommended) (y/n): "
    if /i "%DELETE%"=="y" (
        echo Deleting old virtual environment...
        rmdir /s /q venv
        echo Deleted.
        echo.
    )
)

REM Create virtual environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created.
) else (
    echo Using existing virtual environment.
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo.

REM Verify we're in venv
where python
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
echo.

REM Install packages with specific versions for compatibility
echo ============================================================
echo Installing packages (this may take 5-10 minutes)...
echo ============================================================
echo.

echo [1/6] Installing PyQt5...
pip install PyQt5==5.15.10
if errorlevel 1 (
    echo WARNING: PyQt5 installation had issues
)
echo.

echo [2/6] Installing pyserial...
pip install pyserial==3.5
echo.

echo [3/6] Installing NumPy (compatible version)...
REM For Python 3.14, try installing numpy from nightly builds
echo %PYVER% | findstr /C:"3.14" >nul
if %errorlevel%==0 (
    echo Python 3.14 detected - trying pre-release NumPy...
    pip install --pre numpy
) else (
    pip install "numpy>=1.21.0,<2.0.0"
)
if errorlevel 1 (
    echo.
    echo NumPy installation failed!
    echo This is likely because Python 3.14 is too new.
    echo.
    echo SOLUTION: Install Python 3.11 or 3.12 instead.
    echo.
    pause
    exit /b 1
)
echo.

echo [4/6] Installing OpenCV...
pip install opencv-python==4.10.0.84
if errorlevel 1 (
    echo WARNING: Specific OpenCV version failed, trying latest compatible...
    pip install opencv-python
)
echo.

echo [5/6] Installing Matplotlib...
pip install "matplotlib>=3.3.0,<4.0.0"
echo.

echo [6/6] Installing SciPy...
pip install "scipy>=1.7.0"
if errorlevel 1 (
    echo WARNING: SciPy installation had issues (optional for basic features)
)
echo.

REM Verify installation
echo ============================================================
echo Verifying installation...
echo ============================================================
echo.

python -c "import PyQt5; print('✓ PyQt5:', PyQt5.__version__)" 2>nul
if errorlevel 1 (
    echo ✗ PyQt5 - FAILED
    set INSTALL_FAILED=1
)

python -c "import serial; print('✓ pyserial:', serial.VERSION)" 2>nul
if errorlevel 1 (
    echo ✗ pyserial - FAILED
    set INSTALL_FAILED=1
)

python -c "import numpy; print('✓ NumPy:', numpy.__version__)" 2>nul
if errorlevel 1 (
    echo ✗ NumPy - FAILED
    set INSTALL_FAILED=1
)

python -c "import cv2; print('✓ OpenCV:', cv2.__version__)" 2>nul
if errorlevel 1 (
    echo ✗ OpenCV - FAILED
    set INSTALL_FAILED=1
)

python -c "import matplotlib; print('✓ Matplotlib:', matplotlib.__version__)" 2>nul
if errorlevel 1 (
    echo ✗ Matplotlib - FAILED
)

python -c "import scipy; print('✓ SciPy:', scipy.__version__)" 2>nul
if errorlevel 1 (
    echo ✗ SciPy - FAILED (optional)
)

echo.

if defined INSTALL_FAILED (
    echo ============================================================
    echo Installation FAILED - some packages didn't install
    echo ============================================================
    echo.
    echo Most likely cause: Python 3.14 is too new
    echo.
    echo SOLUTION:
    echo   1. Install Python 3.11.9 from https://www.python.org/downloads/
    echo   2. During installation, check "Add Python to PATH"
    echo   3. Run: py -3.11 -m venv venv
    echo   4. Run this setup script again
    echo.
    pause
    exit /b 1
)

echo ============================================================
echo Installation Complete!
echo ============================================================
echo.
echo ✓ All core packages installed successfully
echo.
echo Next steps:
echo   1. Run: run_asgard_enhanced.bat
echo   2. Or run minimal version: python asgard_minimal.py
echo.
echo Optional packages:
echo   Kinect v1:    pip install freenect
echo   Kinect v2:    pip install pylibfreenect2
echo   Azure Kinect: pip install pyk4a
echo   Sensors:      pip install smbus2
echo.

deactivate
pause
