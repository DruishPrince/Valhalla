@echo off
REM ========================================
REM Diagnostic Script for Numpy Issues
REM ========================================

echo ========================================
echo Numpy Issue Diagnostic Tool
echo ========================================
echo.

echo Checking environment...
echo ========================================
echo.

echo Current Directory:
cd
echo.

echo Checking for conflicting files...
echo ========================================

if exist "numpy.py" (
    echo [WARNING] Found numpy.py file - THIS IS THE PROBLEM!
    echo           This file conflicts with the numpy package.
) else (
    echo [OK] No numpy.py file found
)

if exist "numpy\" (
    echo [WARNING] Found numpy folder - THIS COULD BE THE PROBLEM!
    echo           This folder might conflict with the numpy package.
) else (
    echo [OK] No numpy folder found
)

if exist "cv2.py" (
    echo [WARNING] Found cv2.py file - THIS COULD BE THE PROBLEM!
) else (
    echo [OK] No cv2.py file found
)

if exist "cv2\" (
    echo [WARNING] Found cv2 folder - THIS COULD BE THE PROBLEM!
) else (
    echo [OK] No cv2 folder found
)

echo.
echo Checking Python environment...
echo ========================================

if exist "venv\Scripts\python.exe" (
    echo [OK] Virtual environment found

    call venv\Scripts\activate.bat

    echo.
    echo Python version:
    python --version

    echo.
    echo Installed packages:
    echo ========================================
    pip list | findstr /i "numpy opencv pyqt5 pyserial pygame matplotlib scipy"

    echo.
    echo Checking numpy installation location...
    echo ========================================
    python -c "import sys; import os; [print(p) for p in sys.path if 'site-packages' in p or 'Valhalla' in p]"

    echo.
    echo Testing imports...
    echo ========================================

    echo Testing numpy...
    python -c "import numpy; print('[OK] Numpy imported successfully, version:', numpy.__version__)" 2>&1

    echo.
    echo Testing cv2...
    python -c "import cv2; print('[OK] OpenCV imported successfully, version:', cv2.__version__)" 2>&1

    echo.
    echo Testing PyQt5...
    python -c "from PyQt5 import QtCore; print('[OK] PyQt5 imported successfully')" 2>&1

) else (
    echo [ERROR] Virtual environment not found!
    echo         Please create it first with: python -m venv venv
)

echo.
echo ========================================
echo Diagnostic complete!
echo ========================================
echo.
echo If you saw any [WARNING] messages above,
echo run fix_numpy_issue.bat to resolve them.
echo.

pause
