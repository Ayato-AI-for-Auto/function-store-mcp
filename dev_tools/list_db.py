import os
import sys

import duckdb

# Add backend to path
sys.path.insert(0, os.path.join(os.getcwd(), "backend"))

from mcp_core.core import config


def list_all():
    db_path = str(config.DB_PATH)
    print(f"DB Path: {db_path}")
    if not os.path.exists(db_path):
        print("DB file does NOT exist at this path.")
        return

    try:
        conn = duckdb.connect(db_path, read_only=True)
        rows = conn.execute("SELECT name, status FROM functions").fetchall()
        print(f"Total functions: {len(rows)}")
        for r in rows:
            print(f" - {r[0]} ({r[1]})")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    list_all()
