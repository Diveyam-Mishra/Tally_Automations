@echo off
chcp 65001 >nul
title Generate Route Delivery & Reconciliation Sheet
color 0E

echo ================================================================
echo    HALDIRAM DELIVERY & CASH RECONCILIATION EXCEL GENERATOR
echo ================================================================
echo.
echo Connecting to FieldAssist to list active shipments...
echo.

cd /d "%~dp0Haldiram"
python generate_delivery_reconciliation.py

echo.
pause
