@echo off
title AstroGen Space Studio
cd /d "%~dp0"

REM Check if virtual env and node_modules already exist for fast boot
if exist ".venv\Scripts\python.exe" (
    if exist "frontend\node_modules" (
        REM Launch silently via pythonw and exit CMD instantly
        start "" ".venv\Scripts\pythonw.exe" frontend\main.py
        exit /b 0
    )
)

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is required to run AstroGen.
    echo Please download and install it from: https://nodejs.org/
    pause
    exit /b 1
)

REM Set up Python virtual environment if missing
if not exist ".venv\Scripts\python.exe" (
    echo Setting up Python virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create Python virtual environment.
        echo Make sure Python 3.10+ is installed.
        pause
        exit /b 1
    )
)

REM Install launcher dependencies if missing
.venv\Scripts\python.exe -c "import PyQt6.QtWebEngineWidgets, requests" >nul 2>&1
if errorlevel 1 (
    echo Installing launcher components [first run only]...
    .venv\Scripts\python.exe -m pip install --upgrade pip -q
    .venv\Scripts\python.exe -m pip install PyQt6 PyQt6-WebEngine requests -q
)

REM Install Node/frontend dependencies if missing
if not exist "frontend\node_modules" (
    echo Installing frontend packages [first run only]...
    cd frontend
    call npx -y pnpm install
    cd ..
)

REM Create required directories
if not exist "models\lora" mkdir models\lora
if not exist "models\vae_gan" mkdir models\vae_gan
if not exist "models\blip2" mkdir models\blip2
if not exist "data\generated" mkdir data\generated

REM Create .env if it doesn't exist
if not exist ".env" (
    echo GEMINI_API_KEY=> .env
    echo ASTROGEN_BACKEND=cpu>> .env
)

REM Create app_state.json if missing
if not exist "data\app_state.json" (
    echo {"launch_count":0,"kaggle_connected":false,"kaggle_url":""}> data\app_state.json
)

REM Launch the AstroGen desktop app
start "" ".venv\Scripts\pythonw.exe" frontend\main.py
exit /b 0
