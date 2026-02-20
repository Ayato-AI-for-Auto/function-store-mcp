import json
import os
import sys
from pathlib import Path
from typing import Dict

SERVER_NAME = "function-store"


def get_mcp_entry() -> Dict:
    """Generate the MCP server entry JSON, adapting to frozen or dev environment."""
    if getattr(sys, "frozen", False):
        # Frozen .exe environment
        exe_path = sys.executable.replace("\\", "/")
        return {
            "command": exe_path,
            "args": ["--server"],
        }
    else:
        # Development environment
        project_dir = Path(__name__).parent.parent.parent.parent.resolve()
        main_py = str(project_dir / "main.py").replace("\\", "/")
        return {
            "command": "uv",
            "args": [
                "run",
                "--project",
                str(project_dir).replace("\\", "/"),
                "--no-sync",
                "python",
                main_py,
                "--server",
            ],
        }


def get_config_paths() -> Dict[str, Path]:
    """Return dict of client_name -> config_path."""
    home = Path.home()
    appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
    return {
        "cursor": home / ".cursor" / "mcp.json",
        "antigravity": home / ".gemini" / "antigravity" / "mcp_config.json",
        "claude": appdata / "Claude" / "claude_desktop_config.json",
        "gemini": home / ".gemini" / "settings.json",
    }


def register_with_client(client_name: str) -> str:
    """Registers the MCP server with a specific client."""
    paths = get_config_paths()
    if client_name not in paths:
        return f"Error: Unknown client '{client_name}'"

    path = paths[client_name]
    try:
        config = {}
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)

        if "mcpServers" not in config:
            config["mcpServers"] = {}

        config["mcpServers"][SERVER_NAME] = get_mcp_entry()

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        return f"SUCCESS: Registered with {client_name}."
    except Exception as e:
        return f"Error: Failed to register with {client_name}: {e}"


def unregister_from_client(client_name: str) -> str:
    """Unregisters the MCP server from a specific client."""
    paths = get_config_paths()
    if client_name not in paths:
        return f"Error: Unknown client '{client_name}'"

    path = paths[client_name]
    if not path.exists():
        return f"Info: Config for {client_name} not found."

    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)

        if "mcpServers" in config and SERVER_NAME in config["mcpServers"]:
            del config["mcpServers"][SERVER_NAME]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return f"SUCCESS: Unregistered from {client_name}."

        return f"Info: Not registered with {client_name}."
    except Exception as e:
        return f"Error: Failed to unregister from {client_name}: {e}"


def get_registration_status() -> Dict[str, bool]:
    """Returns the registration status for all supported clients."""
    paths = get_config_paths()
    status = {}
    for name, path in paths.items():
        if not path.exists():
            status[name] = False
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
            status[name] = SERVER_NAME in config.get("mcpServers", {})
        except Exception:
            status[name] = False
    return status
