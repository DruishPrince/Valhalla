@echo off
REM Launch Asgard Enhanced GUI
REM Windows batch script

echo ========================================
echo Asgard Enhanced - Thor Robotic Arm
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo.
    echo Please run setup first:
    echo   setup_windows.bat
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated
echo.

REM Check if asgard_enhanced.py exists
if not exist "asgard_enhanced.py" (
    echo ERROR: asgard_enhanced.py not found!
    echo Make sure you are in the correct directory.
    pause
    deactivate
    exit /b 1
)

REM Launch GUI with error handling
echo Starting Asgard Enhanced GUI...
echo.
echo If you see errors about missing modules:
echo   - Run setup_windows.bat to install dependencies
echo   - Or manually run: pip install PyQt5 pyserial opencv-python numpy matplotlib scipy
echo.
echo ========================================
echo.

python asgard_enhanced.py
set ERRORCODE=%ERRORLEVEL%

echo.
echo ========================================

if %ERRORCODE% neq 0 (
    echo.
    echo ERROR: Program exited with error code %ERRORCODE%
    echo.
    echo Common issues:
    echo   1. Missing PyQt5: pip install PyQt5
    echo   2. Missing dependencies: Run setup_windows.bat
    echo   3. Check error messages above for details
    echo.
)

REM Deactivate on exit
deactivate

pause
