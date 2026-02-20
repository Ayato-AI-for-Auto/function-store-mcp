import json
import logging
import os
import shutil
import sys
import time

# Setup paths
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Isolation environment
test_base = os.path.join(project_root, "dev_tools", "env_test_draft")
if os.path.exists(test_base):
    shutil.rmtree(test_base)
os.makedirs(test_base)

os.environ["FS_DATA_DIR"] = os.path.join(test_base, "data")
os.environ["MODEL_TYPE"] = "local"  # Use fastembed locally

from mcp_core.core.database import get_db_connection, init_db
from mcp_core.engine.logic import do_save_impl, do_search_impl

# Setup logging
logging.basicConfig(level=logging.INFO)


def wait_for_indexing(expected_count=3):
    print(f"Waiting for indexing ({expected_count} entries)...")
    for i in range(30):
        try:
            with get_db_connection() as conn:
                count = conn.execute("SELECT count(*) FROM embeddings").fetchone()[0]
                if count >= expected_count:
                    print(f"Indexing complete ({count} entries).")
                    return True
        except:
            pass
        time.sleep(1)
    print("Timeout waiting for indexing.")
    return False


def test_draft_save():
    init_db()

    # 1. Save with EMPTY description
    print("\n--- Saving with empty description ---")
    res1 = do_save_impl(
        asset_name="empty_desc_func",
        code="def hello(): return 'world'",
        description="",
        tags=["test"],
    )
    print(f"Result: {res1}")

    # 2. Save with SYNTAX error
    print("\n--- Saving with syntax error ---")
    res2 = do_save_impl(
        asset_name="broken_syntax_func",
        code="def broken(:\n    print('oops')",
        description="This is a broken draft",
        tags=["broken"],
    )
    print(f"Result: {res2}")

    # 3. Save a VALID function for comparison (same keywords)
    print("\n--- Saving a valid function ---")
    res3 = do_save_impl(
        asset_name="valid_printer",
        code="def valid_printer():\n    print('I am working fine')",
        description="A working printer function",
        tags=["printer"],
    )
    print(f"Result: {res3}")

    if not wait_for_indexing(3):
        return

    # 4. Search and check ranking
    print("\n--- Searching for 'printer' or 'syntax' ---")
    search_res = do_search_impl("printer logic", limit=5)

    print("\nSearch Results (Ordered by score):")
    for r in search_res:
        print(
            f"Name: {r['name']}, Score: {r['score']}, Quality: {r['quality_score']}, Status: {r['status']}"
        )
        if r["name"] == "empty_desc_func":
            print(f"  Check Desc: {r['description']}")

    # Valid one should be higher than broken one if they matched
    # But here 'valid_printer' matches 'printer' better than 'broken_syntax_func'
    # Let's check descriptions
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT description, status, metadata FROM functions WHERE name='empty_desc_func'"
        ).fetchone()
        print("\nDB State for 'empty_desc_func':")
        print(f"  Description: {row[0]}")
        print(f"  Status: {row[1]}")

        row2 = conn.execute(
            "SELECT description, status, metadata FROM functions WHERE name='broken_syntax_func'"
        ).fetchone()
        print("\nDB State for 'broken_syntax_func':")
        print(f"  Description: {row2[0]}")
        print(f"  Status: {row2[1]}")
        meta2 = json.loads(row2[2])
        print(f"  Quality Score: {meta2['quality_score']}")

    if "Draft automatically saved" in row[0] and row2[1] == "broken":
        print("\nSUCCESS: Phase 9 Draft-First functionality verified.")
    else:
        print("\nFAILURE: Expectations not met.")


if __name__ == "__main__":
    test_draft_save()
