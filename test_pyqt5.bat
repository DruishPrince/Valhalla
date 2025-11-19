@echo off
REM Test PyQt5 installation in detail

echo ============================================================
echo PyQt5 Diagnostic Test
echo ============================================================
echo.

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo Python version:
python --version
echo.

echo Python location:
where python
echo.

echo Testing if PyQt5 is installed...
python -c "import PyQt5" 2>nul
if errorlevel 1 (
    echo ✗ PyQt5 is NOT installed
    echo.
    echo Attempting to install PyQt5...
    echo.

    echo Try 1: Standard installation
    pip install PyQt5
    echo.

    python -c "import PyQt5" 2>nul
    if errorlevel 1 (
        echo Still failed. Try 2: Install dependencies first
        pip install PyQt5-sip
        pip install PyQt5-Qt5
        pip install PyQt5
        echo.
    )

    python -c "import PyQt5" 2>nul
    if errorlevel 1 (
        echo Still failed. Try 3: Specific version
        pip install PyQt5==5.15.9
        echo.
    )
) else (
    echo ✓ PyQt5 is installed
)

echo.
echo Testing PyQt5 components...
python -c "import PyQt5.QtCore; print('  ✓ QtCore')" 2>nul || echo   ✗ QtCore
python -c "import PyQt5.QtGui; print('  ✓ QtGui')" 2>nul || echo   ✗ QtGui
python -c "import PyQt5.QtWidgets; print('  ✓ QtWidgets')" 2>nul || echo   ✗ QtWidgets

echo.
echo Testing simple PyQt5 window...
python -c "from PyQt5.QtWidgets import QApplication, QLabel; import sys; app = QApplication(sys.argv); label = QLabel('Test'); print('  ✓ PyQt5 GUI works!')" 2>nul
if errorlevel 1 (
    echo   ✗ PyQt5 GUI test failed
    echo.
    echo Detailed error:
    python -c "from PyQt5.QtWidgets import QApplication, QLabel; import sys; app = QApplication(sys.argv); label = QLabel('Test')"
)

echo.
echo ============================================================
echo.

pause
