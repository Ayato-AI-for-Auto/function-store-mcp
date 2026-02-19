"""
MCP Server Registration Script for Function Store.

Usage:
    python register_mcp.py                  # Register for all detected clients
    python register_mcp.py --cursor         # Register for Cursor only
    python register_mcp.py --claude         # Register for Claude Desktop only
    python register_mcp.py --antigravity    # Register for Antigravity only
    python register_mcp.py --gemini         # Register for Gemini CLI only
    python register_mcp.py --unregister     # Remove from all clients
"""

import argparse
import json
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.resolve()
SERVER_NAME = "function-store"


def _mcp_entry():
    """Generate the MCP server entry JSON."""
    main_py = str(PROJECT_DIR / "main.py").replace("\\", "/")
    return {
        "command": "uv",
        "args": [
            "run",
            "--project",
            str(PROJECT_DIR).replace("\\", "/"),
            "--no-sync",
            "python",
            main_py,
            "--server",
        ],
    }


def _config_paths():
    """Return dict of client_name -> config_path."""
    home = Path.home()
    appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
    return {
        "cursor": home / ".cursor" / "mcp.json",
        "antigravity": home / ".gemini" / "antigravity" / "mcp_config.json",
        "claude": appdata / "Claude" / "claude_desktop_config.json",
        "gemini": home / ".gemini" / "settings.json",
    }


def _read_config(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _write_config(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def register(client: str, path: Path):
    config = _read_config(path)
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    config["mcpServers"][SERVER_NAME] = _mcp_entry()
    _write_config(path, config)
    print(f"  [OK] {client}: Registered in {path}")


def unregister(client: str, path: Path):
    if not path.exists():
        print(f"  [--] {client}: Config not found, skipping.")
        return
    config = _read_config(path)
    if "mcpServers" in config and SERVER_NAME in config["mcpServers"]:
        del config["mcpServers"][SERVER_NAME]
        _write_config(path, config)
        print(f"  [OK] {client}: Unregistered from {path}")
    else:
        print(f"  [--] {client}: Not registered, skipping.")


def main():
    parser = argparse.ArgumentParser(
        description="Register Function Store as an MCP server."
    )
    parser.add_argument(
        "--cursor", action="store_true", help="Register for Cursor only"
    )
    parser.add_argument(
        "--antigravity", action="store_true", help="Register for Antigravity only"
    )
    parser.add_argument(
        "--claude", action="store_true", help="Register for Claude Desktop only"
    )
    parser.add_argument(
        "--gemini", action="store_true", help="Register for Gemini CLI only"
    )
    parser.add_argument("--unregister", action="store_true", help="Remove registration")
    args = parser.parse_args()

    paths = _config_paths()

    # If no specific client flag, do all
    targets = {}
    if args.cursor:
        targets["cursor"] = paths["cursor"]
    elif args.antigravity:
        targets["antigravity"] = paths["antigravity"]
    elif args.claude:
        targets["claude"] = paths["claude"]
    elif args.gemini:
        targets["gemini"] = paths["gemini"]
    else:
        targets = paths

    action = unregister if args.unregister else register
    action_name = "Unregistering" if args.unregister else "Registering"

    print(f"\n  {action_name} Function Store MCP Server...")
    print(f"  Project: {PROJECT_DIR}\n")

    for client, path in targets.items():
        action(client, path)

    if not args.unregister:
        print("\n  Note: Cursor/Antigravity workspace configs are auto-registered via")
        print("        .cursor/mcp.json and .vscode/mcp.json (included in repo).\n")


if __name__ == "__main__":
    main()
