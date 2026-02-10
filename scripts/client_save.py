
import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.types import CallToolRequestParams

# Logic codes
code_install = r'''def install_python_dependencies(dependencies: list[str], base_dir: str = ".mcp_deps") -> tuple[str | None, str]:
    """Installs dependencies using uv into a dedicated directory."""
    import subprocess
    import hashlib
    import os
    from pathlib import Path
    
    if not dependencies: return None, ""
    
    deps_str = "_".join(sorted(dependencies))
    deps_hash = hashlib.sha256(deps_str.encode()).hexdigest()[:16]
    base_path = Path(base_dir).resolve()
    target_dir = base_path / deps_hash / "site-packages"
    
    if target_dir.exists() and any(target_dir.iterdir()):
        return str(target_dir), ""
        
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        # Using list concatenation for cleaner command construction
        cmd = ["uv", "pip", "install", "--target", str(target_dir)]
        cmd.extend(dependencies)
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None, f"Install Failed: {result.stderr}"
        return str(target_dir), ""
    except Exception as e:
        return None, f"Install Error: {e}"
'''

code_secrets = r'''def scan_code_for_secrets(code: str) -> tuple[bool, str]:
    """Scans code for hardcoded secrets using regex."""
    import re
    SECRET_PATTERNS = [
        r'sk-[a-zA-Z0-9]{20,}',
        r'AIza[0-9A-Za-z_-]{35}',
        r'ghp_[a-zA-Z0-9]{36}',
        r'AKIA[0-9A-Z]{16}',
        r'-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----',
    ]
    for pattern in SECRET_PATTERNS:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
             return True, match.group(0)[:20] + "..."
    return False, ""
'''

code_wasm = r'''def setup_wasm_environment(base_dir: str = "bin") -> bool:
    """Downloads CPython Wasm runtime."""
    import urllib.request
    import tarfile
    from pathlib import Path
    
    BIN_DIR = Path(base_dir)
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    WASM_PATH = BIN_DIR / "python.wasm"
    
    if not WASM_PATH.exists():
        try:
            print("Downloading python.wasm...")
            urllib.request.urlretrieve("https://github.com/run-llama/python-wasi/releases/download/v3.12.0/python.wasm", WASM_PATH)
            print("Downloading lib-python.tar.gz...")
            lib_path = BIN_DIR / "lib-python.tar.gz"
            urllib.request.urlretrieve("https://github.com/run-llama/python-wasi/releases/download/v3.12.0/lib-python.tar.gz", lib_path)
            with tarfile.open(lib_path, "r:gz") as tar:
                tar.extractall(path=BIN_DIR)
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    return True
'''

async def save_via_sse():
    url = "http://localhost:8001/sse"
    print(f"Connecting to {url}...")
    
    async with sse_client(url) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            
            tools = await session.list_tools()
            print(f"Connected. Found {len(tools.tools)} tools.")
            
            # 1. Install Dependencies
            print("Saving install_python_dependencies...")
            await session.call_tool("save_function", arguments={
                "name": "install_python_dependencies",
                "code": code_install,
                "description": "Installs Python dependencies via uv.",
                "tags": ["utils", "dependencies"],
                "dependencies": [],
                "test_cases": [],
                "auto_generate_tests": False
            })
            
            # 2. Secret Scan
            print("Saving scan_code_for_secrets...")
            await session.call_tool("save_function", arguments={
                "name": "scan_code_for_secrets",
                "code": code_secrets,
                "description": "Scans code for secrets.",
                "tags": ["security"],
                "dependencies": [],
                "test_cases": [],
                "auto_generate_tests": False
            })
            
             # 3. Wasm Setup
            print("Saving setup_wasm_environment...")
            await session.call_tool("save_function", arguments={
                "name": "setup_wasm_environment",
                "code": code_wasm,
                "description": "Sets up Wasm environment.",
                "tags": ["wasm", "setup"],
                "dependencies": [],
                "test_cases": [],
                "auto_generate_tests": False
            })

            print("All functions saved successfully!")

if __name__ == "__main__":
    asyncio.run(save_via_sse())
