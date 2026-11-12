@echo off
chcp 65001 >nul
title Tally Receipt Voucher Automation
color 0B

echo ============================================================
echo      TALLY RECEIPT AUTOMATION (EXCLUDING SIGNED BILLS)
echo ============================================================
echo.
echo Rule:
echo   - All bills listed in SIGNED_BILLS_INPUT.xlsx are EXCLUDED (kept as Udhaari).
echo   - All other delivered sales bills in the month will have Receipts generated.
echo.

set /p USER_MONTH="Enter Month (MM-YYYY) [e.g. 10-2026] or press ENTER for October 2026: "
if "%USER_MONTH%"=="" set USER_MONTH=10-2026

echo.
echo ============================================================
echo [STEP 1] RUNNING IN PREVIEW (DRY-RUN) MODE...
echo ============================================================
echo.

cd /d "%~dp0Haldiram"
python generate_receipts_for_paid_bills.py --month %USER_MONTH%

if %ERRORLEVEL% neq 0 (
    color 0C
    echo.
    echo [ERROR] An error occurred during preview. Check messages above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo                  CONFIRMATION REQUIRED
echo ============================================================
echo Check the breakdown numbers above.
echo.
echo [Y] YES - Post these receipts into Tally now.
echo [N] NO  - Cancel and do not change anything in Tally.
echo.
set /p CONFIRM="Do you want to push receipts to Tally? (Y/N): "

if /i "%CONFIRM%"=="Y" (
    echo.
    echo ============================================================
    echo [STEP 2] PUSHING RECEIPTS TO TALLY ON 100.103.81.73...
    echo ============================================================
    python generate_receipts_for_paid_bills.py --month %USER_MONTH% --post
    if %ERRORLEVEL% equ 0 (
        color 0A
        echo.
        echo ============================================================
        echo [SUCCESS] Receipts successfully imported into Tally!
        echo ============================================================
    ) else (
        color 0C
        echo.
        echo [ERROR] Failed to post receipts to Tally.
    )
) else (
    color 0E
    echo.
    echo ============================================================
    echo [CANCELLED] Operation cancelled. No changes made in Tally.
    echo ============================================================
)

echo.
pause
