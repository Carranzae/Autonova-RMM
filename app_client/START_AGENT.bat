@echo off
title Autonova RMM - Client Agent
color 0B
cls

echo =============================================
echo    AUTONOVA RMM - CLIENT AGENT SETUP
echo =============================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

echo [1/4] Checking Python version...
python --version

:: Check if virtual environment exists
if not exist "venv" (
    echo.
    echo [2/4] Creating virtual environment...
    python -m venv venv
) else (
    echo [2/4] Virtual environment already exists.
)

:: Activate virtual environment
echo.
echo [3/4] Activating virtual environment...
call venv\Scripts\activate.bat

:: Install dependencies
echo.
echo [4/4] Installing dependencies...
pip install -r requirements.txt --quiet

:: Check for .env file
if not exist ".env" (
    if exist "..\.env.example" (
        echo.
        echo [INFO] Creating .env from template...
        copy "..\.env.example" ".env" >nul
    )
)

echo.
echo =============================================
echo    AGENT STARTING
echo =============================================
echo.
echo    Connecting to server...
echo    Press Ctrl+C to stop the agent
echo.
echo =============================================
echo.

:: Run the agent
python -m src.main

pause
