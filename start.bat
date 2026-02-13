@echo off
REM PenguinMod File Converter - Windows Launcher

echo.
echo 🐧 PenguinMod File Converter
echo ==================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8 or higher from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo ✓ Python is installed
echo.

REM Run the launcher script
python run.py

if errorlevel 1 (
    echo.
    echo ❌ Application encountered an error
    pause
    exit /b 1
)

echo.
echo Application closed successfully
pause
