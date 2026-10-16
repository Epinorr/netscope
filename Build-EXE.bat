@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo NetScope v1.2.0 - Windows EXE Build
echo ==========================================
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.10+ and enable PATH.
  pause
  exit /b 1
)
py -m pip install --upgrade pip
if errorlevel 1 goto :error
py -m pip install -r requirements.txt
if errorlevel 1 goto :error
py -m PyInstaller --noconfirm --clean --windowed --name NetScope --onefile --icon "assets\netscope.ico" --add-data "assets;assets" --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtQuick --exclude-module PySide6.QtQml --exclude-module PySide6.Qt3DCore --exclude-module PySide6.QtMultimedia main.py
if errorlevel 1 goto :error
echo.
echo Build complete: dist\NetScope.exe
pause
exit /b 0
:error
echo.
echo Build failed. Review the error above.
pause
exit /b 1