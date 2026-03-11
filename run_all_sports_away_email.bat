@echo off
REM =========================================================
REM Scraper - WSZYSTKIE SPORTY (GOŚCIE) + EMAIL
REM =========================================================

echo.
echo ============================================================
echo  Livesport H2H Scraper - WSZYSTKIE SPORTY + EMAIL
echo  TRYB: GOŚCIE (AWAY TEAMS) z >=60%% H2H + PRZEWAGA FORMY
echo ============================================================
echo.

REM Ustaw datę (zmień na właściwą)
SET DATE=2025-10-12

echo Data: %DATE%
echo Sporty: Football, Basketball, Volleyball, Handball, Rugby, Hockey
echo Fokus: DRUŻYNY GOŚCI + PRZEWAGA FORMY
echo Email: jakubmajka76@gmail.com
echo.

python scrape_and_notify.py --date %DATE% --sports football basketball volleyball handball rugby hockey --to jakubmajka76@gmail.com --from-email jakubmajka76@gmail.com --password "jtgs vkeg euba yhms" --away-team-focus --only-form-advantage --headless --use-forebet --use-sofascore --use-odds

echo.
echo ============================================================
echo  Gotowe! Email wysłany.
echo ============================================================
echo.
pause

