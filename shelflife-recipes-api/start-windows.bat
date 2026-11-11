@echo off
REM Double-click this file (Windows) to set up and start the ShelfLife API.
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
%PY% --version >nul 2>nul || (echo Python is not installed. Get it from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^) & pause & exit /b 1)
if not exist venv (echo First run: setting up ^(about a minute^)... & %PY% -m venv venv || (echo Setup failed. & pause & exit /b 1))
call venv\Scripts\activate.bat
pip install -q -r requirements-dev.txt || (echo Install failed. & pause & exit /b 1)
echo.
echo   ShelfLife API is running!  Open:  http://127.0.0.1:8000/docs
echo   ^(Leave this window open. Press Ctrl+C to stop.^)
echo.
start "" "http://127.0.0.1:8000/docs"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
