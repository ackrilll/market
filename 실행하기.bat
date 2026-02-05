@echo off
chcp 65001 > nul
cls
echo ========================================
echo   365 Healthy Farm Order Converter
echo ========================================
echo.

REM Current directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo DEBUG: Current directory is %CD%
echo DEBUG: SCRIPT_DIR is %SCRIPT_DIR%
echo.

REM Check for Portable Python
set "PYTHON_PATH="
if exist "python\python.exe" (
    set "PYTHON_PATH=%CD%\python\python.exe"
    echo [OK] Found Portable Python at: %CD%\python\python.exe
) else (
    echo [WARNING] Portable Python not found at: %CD%\python\python.exe
    REM Check system Python
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_PATH=python"
        echo [OK] Using System Python
    ) else (
        echo [ERROR] Python not found
        echo.
        echo Please check:
        echo 1. Python folder exists in this directory
        echo 2. python\python.exe file exists
        echo 3. Or install Python 3.8+ from https://www.python.org/downloads/
        echo.
        dir python /b
        pause
        exit /b 1
    )
)

echo.
"%PYTHON_PATH%" --version
echo.

REM Install packages
echo [Step 1] Installing packages...
echo.
"%PYTHON_PATH%" -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Package installation failed
    pause
    exit /b 1
)

echo.
echo [Step 2] Starting Streamlit server...
echo.
echo ========================================
echo  Browser will open automatically
echo  Press Ctrl+C to stop the server
echo ========================================
echo.

REM Run Streamlit
"%PYTHON_PATH%" -m streamlit run convert.py

pause
