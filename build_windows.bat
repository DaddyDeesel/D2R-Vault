@echo off
REM D2R Vault - Windows build script
REM Produces dist\D2R-Vault.exe using PyInstaller.

setlocal

echo === D2R Vault build ===

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo Building executable with PyInstaller...
pyinstaller ^
    --name "D2R-Vault" ^
    --windowed ^
    --onefile ^
    --icon assets\items\ui\app_icon.ico ^
    --add-data "assets;assets" ^
    --hidden-import "PySide6.QtSvg" ^
    app\main.py

if %ERRORLEVEL% NEQ 0 (
    echo Build failed.
    exit /b 1
)

echo.
echo Build complete: dist\D2R-Vault.exe
echo.
echo NOTE: Tesseract OCR must be installed separately on the target
echo machine (https://github.com/UB-Mannheim/tesseract/wiki), and its
echo install directory added to PATH, or pytesseract.pytesseract.tesseract_cmd
echo set explicitly in app\ocr\ocr_engine.py.

endlocal
