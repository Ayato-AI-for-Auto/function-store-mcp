@echo off
cd /d "%~dp0"

:: -------------------------------------------------------------
:: Function Store MCP Launcher (Lightweight Edition)
:: -------------------------------------------------------------

:: 1. Check for 'uv' (Modern Python Manager)
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] 'uv' command not found.
    echo Please install it: powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
    pause
    exit /b 1
)

:: 2. Environment Setup (Automatic)
if not exist .venv (
    echo [INFO] First-time setup: Creating virtual environment...
    uv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
    echo [INFO] Installing dependencies...
    uv pip install -e .
    if %errorlevel% neq 0 (
        echo [ERROR] Dependency installation failed.
        pause
        exit /b 1
    )
)

:: 3. Check Public Store Connectivity (Optional)
echo [INFO] Environment check complete.
echo [INFO] Mode: Public-First / Local-Compute

:: 4. Launch via main.py
echo [INFO] Launching Function Store...
echo.
.venv\Scripts\python.exe main.py
if %errorlevel% neq 0 (
    echo [ERROR] Dashboard failed to start.
    echo [TIP] Try running: uv pip install -e .
    pause
)