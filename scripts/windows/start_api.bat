@echo off
REM Start Function Store REST API Server

echo Starting Function Store REST API...
echo Server will be available at http://localhost:8000
echo Press Ctrl+C to stop the server
echo.

cd /d "%~dp0.."
.venv\Scripts\python.exe api.py
