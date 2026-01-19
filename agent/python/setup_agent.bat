@echo off
setlocal EnableDelayedExpansion
title UpKeep Agent Setup

echo ========================================================
echo               UpKeep Agent - Easy Setup
echo ========================================================
echo.

REM 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8+ and try again.
    pause
    exit /b
)
echo [OK] Python found.

REM 2. Create Virtual Environment
if not exist venv (
    echo [INFO] Creating virtual environment (venv)...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b
    )
) else (
    echo [INFO] Virtual environment already exists.
)

REM 3. Install Dependencies
echo [INFO] Installing/Updating dependencies...
call venv\Scripts\activate
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b
)

REM 4. Configuration
if not exist agent.config.json (
    echo.
    echo ========================================================
    echo                  Configuration
    echo ========================================================
    echo.
    set /p SERVER_URL="Server URL (e.g. http://192.168.1.10:8000): "
    set /p SERVER_ID="Server ID (e.g. server-01): "
    set /p TOKEN="Token (optional): "
    
    echo {> agent.config.json
    echo   "server": "!SERVER_URL!",>> agent.config.json
    echo   "server_id": "!SERVER_ID!",>> agent.config.json
    echo   "token": "!TOKEN!",>> agent.config.json
    echo   "interval": 60>> agent.config.json
    echo }>> agent.config.json
    
    echo [OK] Configuration saved to agent.config.json
) else (
    echo [INFO] agent.config.json already exists. Skipping configuration.
)

REM 5. Create Start Script
(
    echo @echo off
    echo cd /d "%%~dp0"
    echo call venv\Scripts\activate
    echo echo Starting UpKeep Agent...
    echo python agent.py
    echo if %%errorlevel%% neq 0 pause
) > start_agent.bat

echo.
echo ========================================================
echo               Setup Complete!
echo ========================================================
echo.
echo You can now run the agent using: start_agent.bat
echo.
pause
