@echo off
REM ========================================
REM Test Installation - Verify All Dependencies
REM ========================================

echo ========================================
echo Installation Test Script
echo ========================================
echo.

if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run recreate_venv.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Testing all required imports...
echo ========================================
echo.

set ALL_OK=1

echo [1/7] Testing PyQt5...
python -c "from PyQt5 import QtCore, QtGui, QtWidgets; print('    SUCCESS - PyQt5 version:', QtCore.QT_VERSION_STR)" 2>&1
if errorlevel 1 set ALL_OK=0

echo.
echo [2/7] Testing pyserial...
python -c "import serial; print('    SUCCESS - pyserial imported')" 2>&1
if errorlevel 1 set ALL_OK=0

echo.
echo [3/7] Testing numpy...
python -c "import numpy; print('    SUCCESS - Numpy version:', numpy.__version__)" 2>&1
if errorlevel 1 set ALL_OK=0

echo.
echo [4/7] Testing opencv-python...
python -c "import cv2; print('    SUCCESS - OpenCV version:', cv2.__version__)" 2>&1
if errorlevel 1 set ALL_OK=0

echo.
echo [5/7] Testing matplotlib...
python -c "import matplotlib; print('    SUCCESS - Matplotlib version:', matplotlib.__version__)" 2>&1
if errorlevel 1 set ALL_OK=0

echo.
echo [6/7] Testing scipy...
python -c "import scipy; print('    SUCCESS - Scipy version:', scipy.__version__)" 2>&1
if errorlevel 1 set ALL_OK=0

echo.
echo [7/7] Testing pygame (Xbox controller)...
python -c "import pygame; print('    SUCCESS - Pygame version:', pygame.__version__)" 2>&1
if errorlevel 1 set ALL_OK=0

echo.
echo ========================================

if %ALL_OK%==1 (
    echo.
    echo *** ALL TESTS PASSED! ***
    echo.
    echo Your environment is ready to run Asgard!
    echo.
    echo Available run scripts:
    echo   - run_asgard.bat           ^(Original Asgard with Xbox controller^)
    echo   - run_asgard_enhanced.bat  ^(Enhanced version^)
    echo.
) else (
    echo.
    echo *** SOME TESTS FAILED ***
    echo.
    echo Please run one of these scripts:
    echo   - fix_numpy_issue.bat     ^(Quick fix^)
    echo   - recreate_venv.bat       ^(Complete reset^)
    echo.
)

echo ========================================
echo.

pause
