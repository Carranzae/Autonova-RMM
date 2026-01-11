@echo off
title Autonova RMM - Cloud Server
color 0A
cls

echo =============================================
echo    AUTONOVA RMM - CLOUD SERVER SETUP
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
echo    SERVER READY - Starting on port 8000
echo =============================================
echo.
echo    Dashboard: http://localhost:8000
echo    API Docs:  http://localhost:8000/docs
echo    Health:    http://localhost:8000/health
echo.
echo    Press Ctrl+C to stop the server
echo =============================================
echo.

:: Run the server
python -m uvicorn main:socket_app --host 0.0.0.0 --port 8000 --reload

pause
