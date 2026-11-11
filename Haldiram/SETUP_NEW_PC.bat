@echo off
chcp 65001 >nul
title Setup Environment for Haldiram Tally Sync
color 0B

echo ============================================================
echo   Installing Dependencies for Haldiram - Tally Sync
echo ============================================================
echo.

echo [1/3] Installing Python dependencies...
pip install requests
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install Python requests. Make sure Python 3 is installed and added to PATH.
    pause
    exit /b 1
)

echo.
echo [2/3] Installing Node.js Playwright package...
call npm install playwright
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install Playwright. Make sure Node.js is installed.
    pause
    exit /b 1
)

echo.
echo [3/3] Installing Chromium browser for Playwright...
call npx playwright install chromium
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install Chromium.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo [SUCCESS] Environment setup completed successfully!
echo.
echo Next steps:
echo   1. Run 'node save_login.js' to log into FieldAssist.
echo   2. Run 'START_DAILY_SYNC.bat' to start syncing invoices.
echo ============================================================
echo.
pause
