@echo off
REM Launch Asgard Enhanced GUI
REM Windows batch script

echo ========================================
echo Asgard Enhanced - Thor Robotic Arm
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then: venv\Scripts\activate
    echo Then: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Launch GUI
echo Starting Asgard Enhanced GUI...
echo.
python asgard_enhanced.py

REM Deactivate on exit
deactivate

pause
