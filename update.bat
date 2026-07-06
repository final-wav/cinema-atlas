@echo off
REM Cinema Atlas — Daten aktualisieren (IMAX-Quelle neu ziehen + neu bauen)
cd /d "%~dp0"
python update.py
echo.
pause
