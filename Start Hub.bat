@echo off
rem Starts the Vinted hub and opens it in the browser (http://127.0.0.1:8765).
rem Keep this window open while using the hub. To stop: close the window.
cd /d "%~dp0"
".venv\Scripts\python.exe" -m vinted_hub serve
pause
