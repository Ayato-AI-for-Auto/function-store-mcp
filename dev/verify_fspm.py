import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from function_store_mcp.server import install_package, get_db_connection, get_function

def test_package_manager():
    print("Testing Package Manager Implementation...")
    
    # 1. Clean up
    conn = get_db_connection()
    conn.execute("DELETE FROM installed_packages WHERE package_id = 'test-pack-001'")
    conn.execute("DELETE FROM functions WHERE name LIKE 'pack_func_%'")
    conn.commit()
    conn.close()

    # 2. Local File URL
    json_path = Path("test_package.json").resolve()
    # Ensure correct file URL format for Windows
    path_str = str(json_path).replace("\\", "/")
    if not path_str.startswith("/"):
        path_str = "/" + path_str
    source_url = f"file://{path_str}"
    
    print(f"Installing from: {source_url}")

    # 3. Run Install
    res = install_package(package_id="test-pack-001", source_url=source_url)
    print(res)
    
    # 4. Verifications
    if "installed successfully" not in res:
        print(f"ERROR: Installation failed with message: {res}")
        sys.exit(1)
    
    # Check if functions exist
    f1 = get_function("pack_func_add")
    f2 = get_function("pack_func_numpy")
    
    if "def pack_func_add" not in f1:
        print("ERROR: pack_func_add not found")
        sys.exit(1)
    if "import numpy as np" not in f2:
        print("ERROR: pack_func_numpy not found")
        sys.exit(1)
    
    print("\nVerification Complete! Package manager is working correctly.")

if __name__ == "__main__":
    test_package_manager()