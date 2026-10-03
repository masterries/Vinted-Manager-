@echo off
rem Opens the Vinted Chrome (own profile). Log in there yourself and keep the window open.
cd /d "%~dp0"
".venv\Scripts\python.exe" -m vinted_hub login
timeout /t 5 >nul
