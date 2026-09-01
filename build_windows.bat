@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo === D2R Vault v0.2 Windows build ===
where python >nul 2>nul || (echo Python was not found on PATH.& exit /b 1)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv || exit /b 1
)
call .venv\Scripts\activate.bat

python -m pip install --upgrade pip || exit /b 1
python -m pip install -r requirements.txt || exit /b 1

set "ICON_ARG="
if exist "assets\ui\app_icon.ico" set "ICON_ARG=--icon assets\ui\app_icon.ico"
if exist "assets\items\ui\app_icon.ico" set "ICON_ARG=--icon assets\items\ui\app_icon.ico"

if not exist assets mkdir assets

echo Building executable...
python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --name "D2R-Vault" ^
    --windowed ^
    --onefile ^
    %ICON_ARG% ^
    --add-data "assets;assets" ^
    --hidden-import "PySide6.QtSvg" ^
    app\main.py

if errorlevel 1 (
    echo.
    echo Build failed.
    exit /b 1
)

echo.
echo Build complete: dist\D2R-Vault.exe
echo User data will be stored in %%LOCALAPPDATA%%\D2R Vault\data
echo Tesseract can be selected inside Settings ^> OCR.
endlocal
