@echo off
title Autonova RMM - Full System Launcher
color 0F
cls

echo =============================================
echo    AUTONOVA RMM - COMPLETE SYSTEM LAUNCHER
echo =============================================
echo.
echo This will start all three components:
echo   1. Cloud Server (Port 8000)
echo   2. Admin Dashboard (Port 3000)
echo   3. Client Agent
echo.
echo =============================================
echo.

:: Check prerequisites
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo Install from: https://python.org
    pause
    exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed!
    echo Install from: https://nodejs.org
    pause
    exit /b 1
)

echo [OK] Python found
echo [OK] Node.js found
echo.

:: Create .env files if they don't exist
if not exist ".env.example" (
    echo [WARN] .env.example not found!
)

echo Starting components in separate windows...
echo.

:: Start Cloud Server
echo [1/3] Starting Cloud Server...
start "Autonova - Server" cmd /k "cd /d cloud_server && START_SERVER.bat"
timeout /t 5 /nobreak >nul

:: Start Admin Dashboard
echo [2/3] Starting Admin Dashboard...
start "Autonova - Dashboard" cmd /k "cd /d admin_pwa && START_DASHBOARD.bat"
timeout /t 3 /nobreak >nul

:: Start Client Agent
echo [3/3] Starting Client Agent...
start "Autonova - Agent" cmd /k "cd /d app_client && START_AGENT.bat"

echo.
echo =============================================
echo    ALL COMPONENTS STARTED!
echo =============================================
echo.
echo    Server:    http://localhost:8000
echo    Dashboard: http://localhost:3000
echo    API Docs:  http://localhost:8000/docs
echo.
echo    Login: admin / admin123
echo.
echo    Close this window or press any key...
echo =============================================

pause >nul
