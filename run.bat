@echo off
REM ================================================
REM   Git Auto-Commit Tool  — Windows Launcher
REM ================================================
REM Double-click this file OR run from command prompt.
REM Make sure Python 3 and Git are installed and in PATH.

title Git Auto-Commit Tool

echo.
echo ================================================
echo   Git Auto-Commit Tool  ^|  Educational Use
echo ================================================
echo.

REM Check Python is available
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3 from https://python.org
    pause
    exit /b 1
)

REM Check Git is available
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git not found. Please install Git from https://git-scm.com
    pause
    exit /b 1
)

REM Use custom config if passed as argument, otherwise default
set CONFIG=config.json
if not "%~1"=="" set CONFIG=%~1

REM Check config file exists
if not exist "%CONFIG%" (
    echo [ERROR] Config file not found: %CONFIG%
    echo.
    echo Create a config.json file next to this script.
    pause
    exit /b 1
)

echo Using config: %CONFIG%
echo.

REM Run the Python script
python auto_commit.py "%CONFIG%"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Script encountered an error. See output above.
    pause
    exit /b 1
)

echo.
pause
