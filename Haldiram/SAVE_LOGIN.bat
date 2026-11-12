@echo off
chcp 65001 >nul
title FieldAssist Login & Session Saver
color 0B

echo ============================================================
echo         FIELDASSIST LOGIN & SESSION SAVER
echo ============================================================
echo.
echo Opening Chrome for one-time login...
echo Please log into FieldAssist in the opened browser window.
echo Once you reach the dashboard, your session will be saved!
echo.

cd /d "%~dp0"
node save_login.js

echo.
pause
