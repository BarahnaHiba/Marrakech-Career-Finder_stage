@echo off
cd /d "%~dp0backend"
"%~dp0.venv\Scripts\python.exe" app.py
pause