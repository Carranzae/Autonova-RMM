@echo off
title Autonova RMM - Build Dashboard
color 0E
cls

echo =============================================
echo    AUTONOVA RMM - BUILD PRODUCTION BUNDLE
echo =============================================
echo.

:: Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed!
    pause
    exit /b 1
)

:: Install dependencies if needed
if not exist "node_modules" (
    echo [1/2] Installing dependencies...
    npm install
) else (
    echo [1/2] Dependencies ready.
)

echo.
echo [2/2] Building production bundle...
npm run build

echo.
echo =============================================
echo    BUILD COMPLETE!
echo =============================================
echo.
echo    Output: dist/
echo.
echo    To preview: npm run preview
echo.
echo =============================================

:: Open dist folder
if exist "dist" (
    explorer dist
)

pause
