@echo off
rem Oeffnet den Vinted-Chrome (eigenes Profil). Dort selbst einloggen, Fenster offen lassen.
cd /d "%~dp0"
".venv\Scripts\python.exe" vinted.py login
timeout /t 5 >nul
