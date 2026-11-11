@echo off
title Cream Bell PDF to Tally Sync
color 0b

echo ================================================================
echo       CREAM BELL INVOICE PDF TO TALLY AUTOMATIC IMPORTER
echo ================================================================
echo.
echo Target Company : ANAND MANGAL_FY26-27
echo Tally Host     : 192.168.10.110:9000
echo Bills Folder   : creambell_bills
echo.
echo Make sure TallyPrime is open on the Tally PC (192.168.10.110)
echo with company ANAND MANGAL_FY26-27 loaded.
echo ================================================================
echo.

python import_creambell_pdfs.py

echo.
echo ================================================================
echo All bills processed!
echo ================================================================
pause
