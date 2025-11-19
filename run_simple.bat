@echo off
REM Simple launcher - just runs Python directly
REM Use this if the main launcher has issues

echo ========================================
echo Asgard Enhanced - Simple Launcher
echo ========================================
echo.

REM Try to activate venv if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
    echo.
)

REM Run Python directly
echo Running test_installation.py to check dependencies...
echo.
python test_installation.py

echo.
echo ========================================
echo.

set /p CONTINUE="Continue to launch GUI? (y/n): "
if /i "%CONTINUE%"=="y" (
    echo.
    echo Launching Asgard Enhanced...
    echo.
    python asgard_enhanced.py
) else (
    echo.
    echo Launch cancelled.
)

echo.
pause
