@echo off
title Autonova RMM - Build Agent EXE
color 0E
cls

echo =============================================
echo    AUTONOVA RMM - BUILD AGENT EXECUTABLE
echo =============================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    pause
    exit /b 1
)

:: Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [ERROR] Run START_AGENT.bat first to create venv!
    pause
    exit /b 1
)

echo [1/2] Installing PyInstaller...
pip install pyinstaller --quiet

echo.
echo [2/2] Building executable...
echo This may take a few minutes...
echo.

pyinstaller build.spec --noconfirm

echo.
echo =============================================
echo    BUILD COMPLETE!
echo =============================================
echo.
echo    Executable: dist\autonova_agent.exe
echo.
echo =============================================

:: Open dist folder
if exist "dist\autonova_agent.exe" (
    explorer dist
)

pause
