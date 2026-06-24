@echo off
echo ================================================
echo   Network Monitor - Starting Application
echo ================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo X Python is not installed!
    echo   Please run setup.bat first
    pause
    exit /b 1
)

REM Check if database exists
if not exist "instance\database.db" (
    echo First time setup detected...
    echo Database will be created automatically.
    echo.
)

echo Starting Network Monitor...
echo Access at: http://localhost:5002
echo Login user: admin
echo Password is loaded from .env ADMIN_PASSWORD
echo.
echo Press Ctrl+C to stop the server
echo ================================================
echo.

python app.py

pause
