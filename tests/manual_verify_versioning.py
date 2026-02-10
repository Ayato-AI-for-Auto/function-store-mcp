
import sys
import os
import json

# Add parent dir to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server import save_function, get_function_history, get_function_version, init_db, DB_PATH

print(f"DB PATH: {DB_PATH}")

def run_test():
    print("Initializing DB...")
    init_db()
    
    name = "manual_ver_func"
    
    print("\n--- Saving V1 ---")
    res = save_function(name=name, code="def t(): return 1", description="V1", test_cases=[])
    print(f"Save Result: {res}")
    
    print("\n--- Checking History (Should have V1 current) ---")
    hist = get_function_history(name)
    print(json.dumps(hist, indent=2))
    
    if "error" in hist[0]:
        print("!!! FAIL: Function not found after V1 save")
        return

    print("\n--- Saving V2 ---")
    res = save_function(name=name, code="def t(): return 2", description="V2", test_cases=[])
    print(f"Save Result: {res}")

    print("\n--- Checking History (Should have V2 current, V1 archived) ---")
    hist = get_function_history(name)
    print(json.dumps(hist, indent=2))
    
    if len(hist) < 2:
        print("!!! FAIL: History length < 2")
    else:
        print("SUCCESS: History has >= 2 items")
        
    print("\n--- Verifying Content ---")
    v1 = get_function_version(name, 1)
    print("V1 Data:", v1)
    v2 = get_function_version(name, 2)
    print("V2 Data:", v2)
    
    if v1.get("code") == "def t(): return 1" and v2.get("code") == "def t(): return 2":
        print("SUCCESS: Code content matches")
    else:
        print("FAIL: Code content mismatch")

if __name__ == "__main__":
    run_test()
