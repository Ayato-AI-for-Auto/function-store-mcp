import os
import sys


def run():
    # Get mode from args, default to --dashboard
    mode = sys.argv[1] if len(sys.argv) > 1 else "--dashboard"

    # Ensure backend is in path if needed (though editable install handles this)
    # But just in case for static analysis/scripts
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

    # Startup Sync (One-time pull from Hub)
    from mcp_core.core import config as cfg

    if cfg.SYNC_ENABLED:
        try:
            print("[INFO] Sync: Pulling latest shared functions from Hub...")
            from mcp_core.engine.sync_engine import sync_engine

            sync_engine.pull()
        except Exception as e:
            print(f"[WARNING] Sync: Startup pull failed: {e}")

    if mode == "--server":
        print("[INFO] Starting Function Store MCP Server...")
        from mcp_core.server import main

        main()
    elif mode == "--dashboard":
        print("[INFO] Starting Function Store Dashboard...")
        import flet as ft

        from frontend.dashboard import main as dashboard_main

        ft.run(dashboard_main)
    else:
        print(f"[ERROR] Unknown mode: {mode}")
        print("Usage: python main.py [--dashboard | --server]")
        sys.exit(1)


if __name__ == "__main__":
    run()
