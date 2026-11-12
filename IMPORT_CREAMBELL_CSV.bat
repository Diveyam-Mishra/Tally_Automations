@echo off
title Cream Bell CSV to Tally Sync
color 0b

echo ================================================================
echo       CREAM BELL CSV TO TALLY AUTOMATIC IMPORTER
echo ================================================================
echo.
echo Target Company : ANAND MANGAL_FY26-27
echo ================================================================
echo.

cd /d "%~dp0Cream-Bell"
python import_creambell_csv.py %*

echo.
echo ================================================================
echo CSV import finished!
echo ================================================================
pause
