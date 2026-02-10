
import os
import sys
from pathlib import Path

# Add src to sys.path
BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR / "src"))

from function_store_mcp.server import _install_dependencies, _run_test_cases

def test_hybrid_runtime():
    print("--- Test 1: Pure Python (Wasm) ---")
    deps_pure = ["requests"]
    path, is_pure, err = _install_dependencies(deps_pure)
    print(f"Deps: {deps_pure}, Path: {path}, Is Pure: {is_pure}, Error: {err}")
    
    code_pure = "def func(x): return x + 1"
    tests_pure = [{"input": {"x": 1}, "expected": 2}]
    
    if path:
        print(f"DEBUG: path exists: {path.exists()}")
    
    print("Running _run_test_cases for Pure Python...")
    passed, log = _run_test_cases(code_pure, tests_pure, path, is_pure)
    print(f"Passed Test 1: {passed}")
    if not passed:
        print(f"LOG 1 START\n{log}\nLOG 1 END")
    
    print("\n--- Test 2: C-Extension (Subprocess) ---")
    deps_c = ["numpy"] 
    path_c, is_pure_c, err_c = _install_dependencies(deps_c)
    print(f"Deps: {deps_c}, Path: {path_c}, Is Pure: {is_pure_c}, Error: {err_c}")
    if path_c:
        print(f"DEBUG: site-packages exists: {path_c.exists()}")
        print(f"DEBUG: site-packages contents: {list(path_c.iterdir())[:5]}")
    
    code_c = """
import numpy as np
def func(x):
    return int(np.array([x]).sum())
"""
    tests_c = [{"input": {"x": 5}, "expected": 5}]
    
    print("Running _run_test_cases for C-Extension...")
    passed_c, log_c = _run_test_cases(code_c, tests_c, path_c, is_pure_c)
    print(f"Passed Test 2: {passed_c}")
    print(f"LOG 2 START\n{log_c}\nLOG 2 END")
    if passed_c:
        print("SUCCESS: Subprocess Isolation (C-Extension) works!")

if __name__ == "__main__":
    try:
        test_hybrid_runtime()
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
