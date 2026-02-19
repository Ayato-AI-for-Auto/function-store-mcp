@echo off
cd /d "%~dp0"
:: Developer Shortcut
:: Usage: dev.bat [--lint-only | --test-only]
.venv\Scripts\python.exe dev_tools\dev.py %*
if %errorlevel% neq 0 (
    echo [ERROR] Pipeline failed.
    exit /b %errorlevel%
)
