@echo off
title AstroGen
color 0B

cd /d "%~dp0"

:: ── Check uv ──────────────────────────────────────────────────
uv --version >nul 2>&1
if errorlevel 1 (
    powershell -WindowStyle Hidden -Command "irm https://astral.sh/uv/install.ps1 | iex" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Could not install uv. Install from: https://docs.astral.sh/uv/
        pause & exit /b 1
    )
)

:: ── Create venv ───────────────────────────────────────────────
if not exist ".venv" (
    uv venv .venv >nul 2>&1
)

:: ── Install packages ──────────────────────────────────────────
.venv\Scripts\python.exe -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    uv pip install -r requirements-app.txt --python .venv\Scripts\python.exe >nul 2>&1
)

:: ── Create .env ───────────────────────────────────────────────
if not exist ".env" echo GEMINI_API_KEY=> .env

:: ── Create folders ────────────────────────────────────────────
if not exist "models\lora"    mkdir models\lora >nul 2>&1
if not exist "models\vae_gan" mkdir models\vae_gan >nul 2>&1
if not exist "models\blip2"   mkdir models\blip2 >nul 2>&1
if not exist "data\generated" mkdir data\generated >nul 2>&1

:: ── Start backend silently ────────────────────────────────────
start "" /B .venv\Scripts\python.exe backend\main.py > backend_log.txt 2>&1
timeout /t 3 /nobreak >nul

:: ── Launch frontend (no CMD window shown to user) ─────────────
start "" /B .venv\Scripts\pythonw.exe frontend\frontend_main.py >nul 2>&1
if errorlevel 1 (
    .venv\Scripts\python.exe frontend\frontend_main.py
)

:: ── Wait and cleanup ──────────────────────────────────────────
timeout /t 2 /nobreak >nul
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":8000" 2^>nul') do (
    taskkill /F /PID %%p >nul 2>&1
)
