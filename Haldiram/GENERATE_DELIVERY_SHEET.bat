@echo off
title Delivery & Collection Reconciliation Generator
color 0b

echo ================================================================
echo    HALDIRAM DELIVERY & CASH RECONCILIATION EXCEL GENERATOR
echo ================================================================
echo.
echo Connecting to FieldAssist to list active shipments...
echo.

python generate_delivery_reconciliation.py

echo.
pause
