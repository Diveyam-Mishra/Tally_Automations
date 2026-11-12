@echo off
chcp 65001 >nul
title Haldiram Daily Sales Sync
color 0A

echo ============================================================
echo           HALDIRAM DAILY SALES SYNC TO TALLY
echo ============================================================
echo.
echo Pipeline:
echo   [1] Auto-Checks FieldAssist login (prompts if expired)
echo   [2] Downloads delivered invoices from FieldAssist
echo   [3] Imports Sales Vouchers into Tally (skips duplicates)
echo.
echo *(Receipt generation is separate via GENERATE_RECEIPTS.bat)*
echo.

:: 1. Check if Tally is running
tasklist /FI "IMAGENAME eq tally.exe" 2>NUL | find /I /N "tally.exe">NUL
if "%ERRORLEVEL%"=="1" (
    color 0C
    echo [ERROR] Tally is NOT running!
    echo.
    echo Please open TallyPrime first and select the company:
    echo   Company: ANAND MANGAL_FY26-27
    echo.
    echo After opening Tally, press any key to continue...
    pause >nul
    color 0A
)

:: 2. Ask for date or default to today
echo.
echo For TODAY'S invoices: Press ENTER directly.
echo For a SPECIFIC DATE  : Type the date in DD-MM-YYYY format (e.g. 03-10-2026)
echo.
set /p USER_DATE="Enter Date (DD-MM-YYYY) or press ENTER for today: "

if "%USER_DATE%"=="" (
    :: Get today's date in DD-MM-YYYY
    for /f "tokens=1-3 delims=/-. " %%a in ("%date%") do (
        set USER_DATE=%%a-%%b-%%c
    )
)

echo.
echo ============================================================
echo Starting Sales Sync for Date: %USER_DATE%
echo Please wait 1 to 2 minutes...
echo ============================================================
echo.

cd /d "%~dp0"
python sync_date.py %USER_DATE%

if %ERRORLEVEL% equ 0 (
    color 0A
    echo.
    echo ============================================================
    echo [SUCCESS] Sales Invoices successfully synchronized to Tally!
    echo.
    echo Open Tally -^> Day Book (Shortcut: K) to verify your vouchers.
    echo ============================================================
) else (
    color 0C
    echo.
    echo ============================================================
    echo [WARNING] An issue occurred during sync. Please check logs above.
    echo ============================================================
)

echo.
echo Press any key to close this window...
pause >nul
