@echo off
REM ========================================
REM Install Pygame - Handles Python 3.12+ Issues
REM ========================================

echo ========================================
echo Pygame Installation Script
echo ========================================
echo.
echo This script handles the pygame installation issues
echo with Python 3.12+ where distutils was removed.
echo.

if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run recreate_venv.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Checking Python version...
python --version
echo.

echo Upgrading pip and setuptools first...
python -m pip install --upgrade pip setuptools wheel
echo.

echo ========================================
echo Attempting pygame installation methods...
echo ========================================
echo.

echo Method 1: Pre-built wheel only...
pip install pygame --only-binary :all:
if not errorlevel 1 goto success

echo.
echo Method 1 failed, trying Method 2: Specific version 2.5.2...
pip install pygame==2.5.2 --only-binary :all:
if not errorlevel 1 goto success

echo.
echo Method 2 failed, trying Method 3: pygame-ce (community edition)...
pip install pygame-ce
if not errorlevel 1 goto success_ce

echo.
echo Method 3 failed, trying Method 4: Force older pip behavior...
pip install setuptools==68.0.0
pip install pygame==2.5.2
if not errorlevel 1 goto success

echo.
echo ========================================
echo ALL METHODS FAILED
echo ========================================
echo.
echo Your Python version may not have pre-built pygame wheels available.
echo.
echo Options:
echo   1. Install Python 3.11 (recommended for best compatibility)
echo   2. Use Windows Subsystem for Linux (WSL)
echo   3. Run Asgard without Xbox controller support
echo.
echo To use Asgard without Xbox controller:
echo   - Edit asgard.py
echo   - Comment out: from xbox_controller import XboxControllerThread
echo   - Comment out: Xbox controller initialization lines
echo.
pause
exit /b 1

:success
echo.
echo ========================================
echo SUCCESS: pygame installed!
echo ========================================
echo.
echo Testing pygame...
python -c "import pygame; pygame.init(); print('Pygame version:', pygame.__version__); print('Joystick module:', pygame.joystick.get_init())"
echo.
pause
exit /b 0

:success_ce
echo.
echo ========================================
echo SUCCESS: pygame-ce (community edition) installed!
echo ========================================
echo.
echo Note: pygame-ce is a drop-in replacement for pygame
echo       All Xbox controller features will work the same.
echo.
echo Testing pygame-ce...
python -c "import pygame; pygame.init(); print('Pygame-CE version:', pygame.__version__); print('Joystick module:', pygame.joystick.get_init())"
echo.
pause
exit /b 0
