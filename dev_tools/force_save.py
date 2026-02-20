import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.getcwd(), "backend"))

from mcp_core.core import config
from mcp_core.core.database import init_db
from mcp_core.engine.logic import do_get_details_impl, do_save_impl


def force_verify():
    print(f"Using DB at: {config.DB_PATH}")
    init_db()

    code = """
import httpx
def check_status(url):
    return httpx.get(url).status_code
"""
    print("Saving...")
    result = do_save_impl(
        asset_name="check_http_status",
        code=code,
        description="Check HTTP status using httpx",
        dependencies=["httpx"],
        skip_test=True,
    )
    print(f"Save Result: {result}")

    print("Checking immediately...")
    details = do_get_details_impl("check_http_status")
    if "error" in details:
        print(f"Error: {details['error']}")
    else:
        print(f"Found Function: {details['name']} (Status: {details['status']})")


if __name__ == "__main__":
    force_verify()
