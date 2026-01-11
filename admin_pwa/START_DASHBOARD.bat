@echo off
title Autonova RMM - Admin Dashboard
color 0D
cls

echo =============================================
echo    AUTONOVA RMM - ADMIN DASHBOARD SETUP
echo =============================================
echo.

:: Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH!
    echo Please install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)

echo [1/3] Checking Node.js version...
node --version

:: Check if npm is available
npm --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm is not available!
    pause
    exit /b 1
)

echo [2/3] npm version:
npm --version

:: Install dependencies if node_modules doesn't exist
if not exist "node_modules" (
    echo.
    echo [3/3] Installing dependencies...
    echo This may take a few minutes...
    npm install
) else (
    echo [3/3] Dependencies already installed.
)

echo.
echo =============================================
echo    DASHBOARD READY - Starting Dev Server
echo =============================================
echo.
echo    Local:   http://localhost:3000
echo    Network: Check console for IP
echo.
echo    Login: admin / admin123
echo.
echo    Press Ctrl+C to stop
echo =============================================
echo.

:: Run the dev server
npm run dev

pause
