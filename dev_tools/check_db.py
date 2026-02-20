import json
import os
import sys

import duckdb

# Add backend to path
sys.path.insert(0, os.path.join(os.getcwd(), "backend"))

from mcp_core.core import config


def check():
    db_path = str(config.DB_PATH)
    print(f"Checking DB at: {db_path}")

    # Connect in read-only mode, which is usually safer
    try:
        conn = duckdb.connect(db_path, read_only=True)
        row = conn.execute(
            "SELECT name, status, metadata FROM functions WHERE name = 'check_http_status'"
        ).fetchone()
        if row:
            name, status, meta_json = row
            meta = json.loads(meta_json) if meta_json else {}
            print(f"Function: {name}")
            print(f"Status: {status}")
            print(f"Verified Dependencies: {meta.get('verified_dependencies', 'None')}")

            if meta.get("verified_dependencies"):
                print("SUCCESS: Dependencies found!")
            else:
                print("PENDING or FAILED: No dependencies captured yet.")
        else:
            print("Function not found.")
        conn.close()
    except Exception as e:
        print(f"Error accessing DB: {e}")


if __name__ == "__main__":
    check()
