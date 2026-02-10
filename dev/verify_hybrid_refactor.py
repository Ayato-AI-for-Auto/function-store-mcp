import os
import sys
import json
import time

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from function_store_mcp.server import save_function, get_db_connection

def verify_hybrid_logic():
    print("Testing Hybrid Logic Refactor (Dependency Pooling & Subprocess)...")
    
    # 1. Clean up for test
    conn = get_db_connection()
    conn.execute("DELETE FROM functions WHERE name IN ('test_numpy_refactor', 'test_pure_refactor', 'test_security_fail')")
    conn.commit()
    conn.close()

    # Case A: Pure Python Function
    print("\n[Case A] Pure Python...")
    res_a = save_function(
        name="test_pure_refactor",
        code="def test_pure_refactor(a, b): return a + b",
        description="Simple add",
        test_cases=[{"input": {"a": 1, "b": 2}, "expected": 3}]
    )
    print(res_a)
    assert "active" in res_a

    # Case B: NumPy Function (Requires Env Creation)
    print("\n[Case B] NumPy Function...")
    res_b = save_function(
        name="test_numpy_refactor",
        code="import numpy as np\ndef test_numpy_refactor(data): return float(np.mean(data))",
        description="Mean with numpy",
        dependencies=["numpy"],
        test_cases=[{"input": {"data": [1, 2, 3]}, "expected": 2.0}]
    )
    print(res_b)
    assert "active" in res_b

    # Case C: Security Failure (AST Check)
    print("\n[Case C] Security Failure...")
    res_c = save_function(
        name="test_security_fail",
        code="import os\ndef test_security_fail(): return os.getcwd()",
        description="Should fail security check",
        test_cases=[{"input": {}, "expected": "/"}]
    )
    print(res_c)
    assert "Security Block" in res_c

    print("\nVerification Complete!")

if __name__ == "__main__":
    verify_hybrid_logic()