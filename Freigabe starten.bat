@echo off
rem Startet die lokale Freigabe-Seite und oeffnet sie im Browser.
rem Fenster offen lassen, solange du die Seite benutzt. Beenden: Fenster schliessen.
cd /d "%~dp0"
".venv\Scripts\python.exe" vinted.py freigabe
pause
