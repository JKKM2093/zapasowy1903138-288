@echo off
REM ============================================
REM QUICK TEST - 20 meczów z każdego sportu
REM Czas: ~10-15 minut
REM ============================================

echo.
echo ========================================
echo   TEST WSZYSTKICH SPORTOW
echo   Limit: 20 meczy (szybki test)
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
  --sports football basketball volleyball handball rugby hockey tennis ^
  --to jakubmajka76@gmail.com ^
  --from-email jakubmajka76@gmail.com ^
  --password "jtgs vkeg euba yhms" ^
  --max-matches 20 ^
  --headless ^
  --sort time

echo.
echo ========================================
echo Koniec: %time%
echo Sprawdz email!
echo ========================================
echo.

pause

