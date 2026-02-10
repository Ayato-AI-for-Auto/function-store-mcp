import os
import json
import sys
import shutil
from pathlib import Path

def configure_claude():
    print("=== Claude Desktop Configuration Helper ===")
    print("")

    # 1. Paths
    current_dir = Path(os.getcwd()).resolve()
    venv_python = current_dir / ".venv" / "Scripts" / "python.exe"
    server_script = current_dir / "function_store_mcp" / "server.py"

    if not venv_python.exists():
        print(f"[ERROR] Virtual environment python not found at: {venv_python}")
        print("Please run setup_windows.bat first.")
        return

    # 2. Config Location
    appdata = os.getenv("APPDATA")
    if not appdata:
        print("[ERROR] APPDATA environment variable not found.")
        return

    config_dir = Path(appdata) / "Claude"
    config_path = config_dir / "claude_desktop_config.json"

    # Ensure dir exists
    if not config_dir.exists():
        try:
            config_dir.mkdir(parents=True)
            print(f"[INFO] Created config directory: {config_dir}")
        except Exception as e:
            print(f"[ERROR] Failed to create directory: {e}")
            return

    # 3. Prepare Config Data
    server_config = {
        "command": str(venv_python),
        "args": [str(server_script)],
        "env": {
            "EMBEDDING_MODEL": "BAAI/bge-m3"
        }
    }

    # 4. Load & Merge
    config_data = {"mcpServers": {}}
    
    if config_path.exists():
        print(f"[INFO] Found existing config: {config_path}")
        # Backup
        backup_path = config_path.with_suffix(".json.bak")
        try:
            shutil.copy2(config_path, backup_path)
            print(f"[INFO] Backup created at: {backup_path}")
        except Exception as e:
            print(f"[WARN] Failed to create backup: {e}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    config_data = json.loads(content)
        except json.JSONDecodeError:
            print("[WARN] Existing config was invalid JSON. Overwriting.")
        except Exception as e:
            print(f"[ERROR] Failed to read config: {e}")
            return

    # Ensure mcpServers key exists
    if "mcpServers" not in config_data:
        config_data["mcpServers"] = {}

    # Update Function Store config
    config_data["mcpServers"]["function-store"] = server_config
    
    # 5. Save
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        print("")
        print(f"SUCCESS: Registered 'function-store' to Claude Desktop.")
        print(f"Path: {config_path}")
        print("")
        print("Please restart Claude Desktop to apply changes.")
        
    except Exception as e:
        print(f"[ERROR] Failed to write config: {e}")

if __name__ == "__main__":
    configure_claude()