@echo off
title Cream Bell PDF to Tally Sync
color 0b

echo ================================================================
echo       CREAM BELL INVOICE PDF TO TALLY AUTOMATIC IMPORTER
echo ================================================================
echo.
echo Target Company : ANAND MANGAL_FY26-27
echo Bills Folder   : Cream-Bell\creambell_bills
echo ================================================================
echo.

cd /d "%~dp0Cream-Bell"
python import_creambell_pdfs.py

echo.
echo ================================================================
echo All bills processed!
echo ================================================================
pause
