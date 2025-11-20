@echo off
REM ========================================
REM Run Asgard - Thor Robotic Arm Control
REM With Xbox Controller Support
REM ========================================

echo ========================================
echo Asgard - Thor Robotic Arm
echo With Xbox Controller Support
echo ========================================
echo.

if not exist "asgard.py" (
    echo ERROR: asgard.py not found!
    echo Please run this script from the Valhalla directory.
    pause
    exit /b 1
)

if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo.
    echo Please run one of these setup scripts first:
    echo   - recreate_venv.bat  ^(recommended^)
    echo   - setup_windows.bat
    echo.
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Virtual environment activated
echo.
echo Starting Asgard GUI...
echo.
echo Features:
echo   - Forward Kinematics control
echo   - Xbox Controller support
echo   - Serial communication with Thor arm
echo.
echo If you see errors about missing modules:
echo   - Run test_installation.bat to check your setup
echo   - Run fix_numpy_issue.bat if you have numpy errors
echo   - Run recreate_venv.bat for a complete reset
echo.
echo ========================================
echo.

python asgard.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo.
    echo ERROR: Program exited with error code %errorlevel%
    echo.
    echo Common issues:
    echo   1. Missing dependencies: Run test_installation.bat
    echo   2. Numpy errors: Run fix_numpy_issue.bat
    echo   3. Xbox controller not detected: Make sure pygame is installed
    echo   4. Serial port issues: Check your COM port settings
    echo.
    pause
    exit /b %errorlevel%
)

echo.
echo ========================================
echo Program closed normally
echo ========================================
echo.

pause
