@echo off
cd /d "%~dp0.."
uv run --no-sync python function_store_mcp\server.py --transport sse --port 8001
pause
