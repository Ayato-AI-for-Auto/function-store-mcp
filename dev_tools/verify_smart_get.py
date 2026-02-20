import logging
import os
import shutil
import sys
import time

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Isolate data environment
test_base = os.path.join(os.getcwd(), "dev_tools", "env_test")
os.environ["FS_DATA_DIR"] = os.path.join(test_base, "data")

from mcp_core.core.database import get_db_connection, init_db
from mcp_core.engine.logic import do_save_impl, do_smart_get_impl

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_test_data():
    """Wipe and init DB with some functions."""
    data_dir = os.environ["FS_DATA_DIR"]
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    os.makedirs(data_dir, exist_ok=True)

    init_db()

    # Save a few functions
    do_save_impl(
        "image_resizer",
        "def image_resizer(img, size):\n    return f'Resized image to {size}'",
        "A function to resize images using PIL or opencv.",
        ["image", "utility"],
    )

    do_save_impl(
        "json_validator",
        "def json_validator(data):\n    import json\n    return json.loads(data)",
        "Parses and validates a JSON string.",
        ["json", "data", "utility"],
    )

    do_save_impl(
        "math_adder",
        "def math_adder(a, b):\n    return a + b",
        "Adds two numbers together.",
        ["math", "calculation"],
    )

    print("Waiting for indexing...")
    for _ in range(30):  # Max 30 seconds
        with get_db_connection() as conn:
            count = conn.execute("SELECT count(*) FROM embeddings").fetchone()[0]
            if count >= 3:
                print(f"Indexing complete ({count} entries).")
                break
        time.sleep(1)
    else:
        print("Warning: Indexing timed out.")


def test_smart_get():
    target_dir = os.path.join(os.getcwd(), "dev_tools", "test_smart_get")
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)

    print("\n--- Testing Smart Get with Natural Language Query ---")
    query = "I need something to parse and validate my JSON data strings"
    print(f"Query: '{query}'")

    result = do_smart_get_impl(query=query, target_dir=target_dir)

    print("\nResult:")
    import json

    print(json.dumps(result, indent=2))

    # Check if file exists
    pkg_path = os.path.join(target_dir, "local_pkg", "json_validator.py")
    if os.path.exists(pkg_path):
        print(
            f"\nSUCCESS: Function '{result['selected_function']}' was injected to {pkg_path}"
        )
        with open(pkg_path, "r", encoding="utf-8") as f:
            print(f"File Preview:\n{f.read()[:100]}...")
    else:
        print(f"\nFAILURE: Injected file not found at {pkg_path}")


if __name__ == "__main__":
    setup_test_data()
    test_smart_get()
