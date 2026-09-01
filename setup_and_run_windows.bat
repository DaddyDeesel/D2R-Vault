@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo === D2R Vault v0.2 Setup and Run ===
where python >nul 2>nul || (
  echo Python was not found on PATH.
  echo Install Python 3.12 or newer, enable "Add Python to PATH", then run this again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv || goto :fail
)
call .venv\Scripts\activate.bat

echo Installing/updating Python dependencies...
python -m pip install --upgrade pip || goto :fail
python -m pip install -r requirements.txt || goto :fail

echo.
echo Starting D2R Vault...
python -m app.main
exit /b %ERRORLEVEL%

:fail
echo.
echo Setup failed. Review the error above.
pause
exit /b 1
