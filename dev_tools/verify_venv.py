import os
import sys
import time

# Add backend to path
sys.path.insert(0, os.path.join(os.getcwd(), "backend"))

print("DEBUG: sys.path =", sys.path)

from mcp_core.core.database import init_db
from mcp_core.engine.logic import do_get_details_impl, do_save_impl

# Initialize DB first
init_db()


def verify_venv_isolation():
    print("Step 1: Saving a function with dependencies...")
    code = """
import httpx
def check_status(url):
    return httpx.get(url).status_code
"""
    result = do_save_impl(
        asset_name="check_http_status",
        code=code,
        description="Check HTTP status using httpx",
        dependencies=["httpx"],
        skip_test=True,  # For faster demonstration
    )
    print(result)

    print("Step 2: Waiting for background maintenance (venv creation + freeze)...")
    # Wait up to 120 seconds for uv venv creation (first time might be slow)
    for i in range(120):
        time.sleep(2)
        try:
            details = do_get_details_impl("check_http_status")
            if "error" in details:
                print(f"Waiting... {i + 1}s (Detail error: {details['error']})")
                continue

            meta = details.get("metadata", {})

            # Check if venv was created and freeze captured
            if meta.get("verified_dependencies"):
                print("-" * 40)
                print("SUCCESS! Versions identified:")
                for pkg in meta["verified_dependencies"]:
                    if "httpx" in pkg or "httpcore" in pkg:
                        print(f"  - {pkg}")
                print("-" * 40)
                return True

            status = details.get("status")
            print(f"Waiting... {i + 1}s (Status: {status})")
        except Exception as de:
            print(f"Waiting... {i + 1}s (DB Contention: {de})")

    print("Fail: Timeout or versions not captured.")
    return False


if __name__ == "__main__":
    try:
        verify_venv_isolation()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
