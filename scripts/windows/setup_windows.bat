@echo off
setlocal

echo ========================================================
echo   Function Store MCP - One-Click Setup (Windows)
echo ========================================================

:: Move to Project Root (parent of utils if running from dist)
if exist "%~dp0..\FunctionStore.bat" (
    cd /d "%~dp0.."
) else (
    cd /d "%~dp0"
)

:: 0. Kill any hanging python processes
echo [INFO] Ensuring no python processes are locking the environment...
taskkill /F /IM python.exe /T >nul 2>nul

:: 1. Check for UV
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] 'uv' not found. Installing uv...
    powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
)

:: 2. Create/Update Virtual Environment
echo.
if exist .venv (
    echo [INFO] Virtual environment exists. Checking health...
) else (
    echo [INFO] Creating new virtual environment...
    uv venv
)

:: 3. Install Dependencies
echo.
echo [INFO] Installing dependencies...

:: Smart Install for PyTorch (CPU/GPU detection)
.venv\Scripts\python.exe scripts\install_torch.py
if %errorlevel% neq 0 goto :error

echo [INFO] Installing project dependencies...
uv pip install -e .

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Dependency installation failed.
    echo [ERROR] This often happens if the environment is corrupted.
    set /p "RETRY=Would you like to DELETE the current environment and start fresh? (y/n): "
    if /i "%RETRY%"=="y" (
        echo [INFO] Deleting .venv...
        rmdir /s /q .venv
        echo [INFO] Restarting setup...
        goto :start_over
    )
    pause
    exit /b 1
)
goto :success

:start_over
uv venv
.venv\Scripts\python.exe scripts\install_torch.py
if %errorlevel% neq 0 goto :error
uv pip install -e .
if %errorlevel% neq 0 goto :error
goto :success

:error
echo [ERROR] Installation failed.
pause
exit /b 1

:success
:: 4. Configure Claude Desktop
echo.
echo [INFO] Configuring Claude Desktop...
.venv\Scripts\python.exe scripts\configure_claude.py

 :: 5. Setup Complete Notification
 echo.
 echo ========================================================
echo   Setup Complete
echo ========================================================
echo.
echo Setup finished. Returning to launcher...
timeout /t 3
