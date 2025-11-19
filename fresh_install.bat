@echo off
REM Complete fresh setup with Python 3.11
REM Deletes everything and starts clean

echo ============================================================
echo Fresh Install with Python 3.11
echo ============================================================
echo.

REM Deactivate any active venv
call deactivate 2>nul

REM Completely remove old venv
echo Removing old virtual environment...
if exist "venv" (
    rmdir /s /q venv
    echo Old venv deleted.
)
echo.

REM Create NEW venv with Python 3.11
echo Creating NEW virtual environment with Python 3.11...
py -3.11 -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create venv with Python 3.11
    echo.
    echo Make sure Python 3.11 is installed:
    py -3.11 --version
    pause
    exit /b 1
)
echo Virtual environment created with Python 3.11
echo.

REM Activate the NEW venv
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Verify Python version in venv
echo Checking Python version in venv:
python --version
echo Python location:
where python
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
echo.

echo ============================================================
echo Installing packages one by one...
echo ============================================================
echo.

REM Install PyQt5 with extra care
echo [1/6] Installing PyQt5...
echo (This is the GUI framework - takes 1-2 minutes)
echo.
python -m pip install --no-cache-dir PyQt5==5.15.10
if errorlevel 1 (
    echo.
    echo PyQt5 installation failed! Trying alternative...
    python -m pip install --no-cache-dir PyQt5
    if errorlevel 1 (
        echo.
        echo PyQt5 still failing. Trying from different source...
        python -m pip install PyQt5-sip
        python -m pip install PyQt5
    )
)

REM Test PyQt5 immediately
echo.
echo Testing PyQt5...
python -c "import PyQt5.QtWidgets; print('  ✓ PyQt5 works!')" 2>nul
if errorlevel 1 (
    echo   ✗ PyQt5 FAILED - cannot continue
    echo.
    echo This might be a system issue. Try:
    echo   1. Restart your computer
    echo   2. Run this script again
    echo   3. Or try: pip install PyQt5-Qt5 PyQt5-sip PyQt5
    pause
    exit /b 1
)
echo.

echo [2/6] Installing pyserial...
python -m pip install pyserial
python -c "import serial; print('  ✓ pyserial works!')"
echo.

echo [3/6] Installing NumPy...
python -m pip install "numpy>=1.21.0,<2.0.0"
python -c "import numpy; print('  ✓ NumPy works!')"
echo.

echo [4/6] Installing OpenCV...
python -m pip install opencv-python
python -c "import cv2; print('  ✓ OpenCV works!')"
echo.

echo [5/6] Installing Matplotlib...
python -m pip install matplotlib
python -c "import matplotlib; print('  ✓ Matplotlib works!')"
echo.

echo [6/6] Installing SciPy...
python -m pip install scipy
python -c "import scipy; print('  ✓ SciPy works!')"
echo.

echo ============================================================
echo Final Verification
echo ============================================================
echo.
python test_installation.py
echo.

echo ============================================================
echo Setup Complete!
echo ============================================================
echo.
echo To run Asgard Enhanced:
echo   run_asgard_enhanced.bat
echo.
echo Or test with minimal version:
echo   python asgard_minimal.py
echo.

pause
