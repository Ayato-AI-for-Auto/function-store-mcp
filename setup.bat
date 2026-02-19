@echo off
cd /d "%~dp0"

:: -------------------------------------------------------------
:: Function Store MCP - Environment Setup
:: -------------------------------------------------------------
:: Usage: Double-click or run from terminal.
:: This script creates a virtual environment and installs all
:: dependencies including local AI models (FastEmbed + Llama.cpp).
:: -------------------------------------------------------------

echo.
echo ============================================
echo   Function Store MCP - Environment Setup
echo ============================================
echo.

:: 1. Check for 'uv'
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] 'uv' command not found.
    echo [INFO]  Install it with:
    echo         powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
    pause
    exit /b 1
)
echo [OK] uv found.

:: 2. Create virtual environment
if not exist .venv (
    echo [INFO] Creating virtual environment...
    uv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment already exists.
)

:: 3. Install core dependencies
echo [INFO] Installing core dependencies...
uv pip install -e .
if %errorlevel% neq 0 (
    echo [ERROR] Core dependency installation failed.
    pause
    exit /b 1
)
echo [OK] Core dependencies installed.

:: 4. Install llama-cpp-python (pre-built CPU wheel)
echo [INFO] Installing llama-cpp-python (CPU pre-built)...
uv pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
if %errorlevel% neq 0 (
    echo [WARNING] llama-cpp-python installation failed.
    echo [INFO]    LLM features will be disabled. Embedding search still works.
    echo [INFO]    For manual fix, see: https://github.com/abetlen/llama-cpp-python
) else (
    echo [OK] llama-cpp-python installed.
)

:: 5. Verify
echo.
echo [INFO] Verifying installation...
.venv\Scripts\python.exe -c "import fastembed; print('[OK] FastEmbed')"
.venv\Scripts\python.exe -c "from llama_cpp import Llama; print('[OK] llama-cpp-python')"
.venv\Scripts\python.exe -c "import duckdb; print('[OK] DuckDB')"

:: 6. Register MCP Server (Cursor Global + Claude Desktop)
echo.
echo [INFO] Registering MCP Server for AI clients...
.venv\Scripts\python.exe register_mcp.py
echo [OK] MCP registration complete.

echo.
echo ============================================
echo   Setup Complete!
echo ============================================
echo.
echo   - Cursor / Antigravity: Auto-registered (workspace config included)
echo   - Claude Desktop:       Registered via register_mcp.py
echo   - Cline:                See README.md for manual setup
echo.
echo   Next: Run FunctionStore.bat to launch the Dashboard.
echo         AI agents can now use Function Store as an MCP server.
echo.
pause
