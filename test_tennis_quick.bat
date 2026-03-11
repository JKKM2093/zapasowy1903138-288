@echo off
REM ============================================
REM QUICK TEST - TENNIS (10 meczów)
REM ============================================

echo.
echo ========================================
echo   TEST TENNIS - 10 meczy
echo ========================================
echo.

cd /d C:\Users\jakub\Downloads\Flashscore2

chcp 65001 >nul
set PYTHONIOENCODING=utf-8

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TODAY=%datetime:~0,4%-%datetime:~4,2%-%datetime:~6,2%

echo Start: %time%
echo Data: %TODAY%
echo.

python scrape_and_notify.py ^
  --date %TODAY% ^
  --sports tennis ^
  --to jakubmajka76@gmail.com ^
  --from-email jakubmajka76@gmail.com ^
  --password "jtgs vkeg euba yhms" ^
  --max-matches 10 ^
  --headless ^
  --sort time

echo.
echo ========================================
echo Koniec: %time%
echo Sprawdz email!
echo ========================================
echo.

pause


