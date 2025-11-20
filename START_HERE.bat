@echo off
REM ========================================
REM Asgard Setup and Launch Helper
REM ========================================

:menu
cls
echo ========================================
echo Asgard - Thor Robotic Arm Control
echo Setup and Launch Helper
echo ========================================
echo.
echo What would you like to do?
echo.
echo   1. Run Asgard (original with Xbox controller)
echo   2. Run Asgard Enhanced
echo   3. Test Installation
echo   4. Diagnose Issues
echo   5. Fix Numpy Error
echo   6. Recreate Virtual Environment (complete reset)
echo   7. Show Xbox Controller Guide
echo   8. Exit
echo.
echo ========================================

set /p choice="Enter your choice (1-8): "

if "%choice%"=="1" goto run_asgard
if "%choice%"=="2" goto run_enhanced
if "%choice%"=="3" goto test
if "%choice%"=="4" goto diagnose
if "%choice%"=="5" goto fix
if "%choice%"=="6" goto recreate
if "%choice%"=="7" goto xbox_guide
if "%choice%"=="8" goto end

echo Invalid choice. Please try again.
timeout /t 2 >nul
goto menu

:run_asgard
cls
call run_asgard.bat
goto menu

:run_enhanced
cls
call run_asgard_enhanced.bat
goto menu

:test
cls
call test_installation.bat
goto menu

:diagnose
cls
call diagnose_issue.bat
goto menu

:fix
cls
call fix_numpy_issue.bat
goto menu

:recreate
cls
call recreate_venv.bat
goto menu

:xbox_guide
cls
echo ========================================
echo Xbox Controller Guide
echo ========================================
echo.
echo The original Asgard now supports Xbox controllers!
echo.
echo CONTROLLER MAPPING:
echo ----------------------------------------
echo.
echo Joysticks:
echo   Left Stick X  : Art1 (Base Rotation)
echo   Left Stick Y  : Art2 (Shoulder)
echo   Right Stick X : Art5 (Wrist Rotation)
echo   Right Stick Y : Art4 (Wrist Pitch)
echo.
echo D-Pad:
echo   Up/Down       : Art3 (Elbow)
echo   Left/Right    : Art6 (Wrist Roll)
echo.
echo Triggers:
echo   Right Trigger : Open Gripper
echo   Left Trigger  : Close Gripper
echo.
echo Buttons:
echo   START         : Homing Cycle
echo   BACK/SELECT   : Zero Position
echo   X             : Kill Alarm
echo   Y             : Toggle Control Mode
echo   B             : Emergency Stop (reserved)
echo.
echo CONTROL MODES:
echo ----------------------------------------
echo.
echo Continuous Mode (default):
echo   - Joystick movements control arm in real-time
echo   - Immediate response
echo.
echo Incremental Mode:
echo   - Joystick sets target position
echo   - Press A button to execute movement
echo.
echo Press Y button to toggle between modes
echo.
echo REQUIREMENTS:
echo ----------------------------------------
echo.
echo   pip install pygame
echo.
echo The controller is automatically detected on startup!
echo Status messages appear in the console.
echo.
echo ========================================
echo.
pause
goto menu

:end
echo.
echo Goodbye!
timeout /t 1 >nul
exit /b 0
