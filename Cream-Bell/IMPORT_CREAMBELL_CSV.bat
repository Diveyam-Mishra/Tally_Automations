@echo off
title Cream Bell CSV to Tally Sync
color 0b

echo ================================================================
echo       CREAM BELL CSV TO TALLYPRIME AUTOMATIC IMPORTER
echo ================================================================
echo.
echo Target Company : ANAND MANGAL_FY26-27
echo Tally Host     : 192.168.10.110:9000
echo.
echo Make sure TallyPrime is open on the Tally PC (192.168.10.110)
echo with company ANAND MANGAL_FY26-27 loaded.
echo ================================================================
echo.

python import_creambell_csv.py

echo.
echo ================================================================
echo All CSV bills processed!
echo ================================================================
pause
