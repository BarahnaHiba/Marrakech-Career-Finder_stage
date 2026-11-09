@echo off
cd /d "%~dp0backend"
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" app.py
) else (
  python app.py
)
pause
