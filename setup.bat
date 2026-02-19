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

:: 6. Register MCP Server (Interactive Selection)
echo.
echo ============================================
echo   MCP Server Registration
echo ============================================
echo.
echo   Which AI client(s) should Function Store connect to?
echo.
echo     [1] Cursor
echo     [2] Antigravity (Gemini)
echo     [3] Claude Desktop
echo     [4] Gemini CLI
echo     [5] All of the above
echo     [0] Skip (register later with register_mcp.py)
echo.
set /p CLIENT_CHOICE="  Enter your choice (0-5): "

if "%CLIENT_CHOICE%"=="0" (
    echo.
    echo   [SKIP] MCP registration skipped.
    echo   [INFO] Run  python register_mcp.py  later to register manually.
    goto :setup_done
)
if "%CLIENT_CHOICE%"=="1" (
    .venv\Scripts\python.exe register_mcp.py --cursor
    goto :setup_done
)
if "%CLIENT_CHOICE%"=="2" (
    .venv\Scripts\python.exe register_mcp.py --antigravity
    goto :setup_done
)
if "%CLIENT_CHOICE%"=="3" (
    .venv\Scripts\python.exe register_mcp.py --claude
    goto :setup_done
)
if "%CLIENT_CHOICE%"=="4" (
    .venv\Scripts\python.exe register_mcp.py --gemini
    goto :setup_done
)
if "%CLIENT_CHOICE%"=="5" (
    .venv\Scripts\python.exe register_mcp.py
    goto :setup_done
)

echo   [ERROR] Invalid choice. Skipping registration.
echo   [INFO]  Run  python register_mcp.py  later to register manually.

:setup_done
echo.
echo ============================================
echo   Setup Complete!
echo ============================================
echo.
echo   Next: Run FunctionStore.bat to launch the Dashboard.
echo         AI agents can now use Function Store as an MCP server.
echo.
pause
