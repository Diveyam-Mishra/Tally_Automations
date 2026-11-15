@echo off
title Cream Bell Excel / CSV to Tally Sync
color 0b

echo ================================================================
echo       CREAM BELL SALES (EXCEL / CSV) TO TALLY IMPORTER
echo ================================================================
echo.
echo Target Company : ANAND MANGAL_FY26-27
echo ================================================================
echo.

cd /d "%~dp0Cream-Bell"
python import_creambell_csv.py %*

echo.
echo ================================================================
echo Import finished! Press any key to close.
echo ================================================================
pause
