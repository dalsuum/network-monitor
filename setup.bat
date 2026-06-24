@echo off
echo ================================================
echo   Network Monitor - Installation Script
echo ================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo X Python is not installed. Please install Python 3.8 or higher.
    echo   Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo âˆš Python found:
python --version
echo.

REM Check if pip is installed
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo X pip is not installed. Please install pip.
    pause
    exit /b 1
)

echo âˆš pip found
echo.

REM Install requirements
echo Installing Python dependencies...
pip install -r requirements.txt

if %errorlevel% equ 0 (
    echo âˆš Dependencies installed successfully
) else (
    echo X Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ================================================
echo   Installation Complete!
echo ================================================
echo.
echo To start the application, run:
echo   python app.py
echo.
echo Then open your browser to:
echo   http://localhost:5002
echo.
echo Login:
echo   Username: admin
echo   Password: set ADMIN_PASSWORD in .env
echo.
echo WARNING: Do not commit .env or real credentials.
echo.
pause
