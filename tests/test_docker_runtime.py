import pytest
from solo_mcp.runtime_docker import docker_runtime

def test_execution():
    if not docker_runtime.is_available():
        pytest.skip("Docker is not available on this system.")
    
    print("=== Docker Runtime Live Test ===")
    
    code = """
def add(a, b):
    return a + b
"""
    test_cases = [
        {"input": {"a": 1, "b": 2}, "expected": 3},
        {"input": {"a": 10, "b": -5}, "expected": 5}
    ]
    
    print("Running 'add' function in container...")
    success, error = docker_runtime.run_function(code, test_cases)
    
    if not success:
        pytest.fail(f"Docker execution failed: {error}")
    
    print("✅ SUCCESS: Function executed and tests passed in container.")
