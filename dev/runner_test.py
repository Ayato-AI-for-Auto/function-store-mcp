
import sys
import json
import traceback

def run_tests():
    # 1. Define User Function
    user_code = 'def func(x): return x + 1'
    namespace = {}
    
    try:
        exec(user_code, namespace)
    except Exception:
        return {"status": "error", "error": "Syntax/Compile Error:\n" + traceback.format_exc()}
    
    # 2. Find function
    candidates = [v for k, v in namespace.items() if callable(v) and k != 'run_tests' and not k.startswith('_')]
    if not candidates:
        return {"status": "error", "error": "No function definition found in code."}
        
    func = candidates[-1]
    
    # 3. Run Tests
    test_cases_raw = '[{"input": {"x": 1}, "expected": 2}]'
    test_cases = json.loads(test_cases_raw)
    errors = []
    
    if not test_cases:
        return {"status": "success"}

    for i, tc in enumerate(test_cases):
        input_args = tc.get("input", {})
        expected = tc.get("expected")
        
        try:
            result = func(**input_args)
            if result != expected:
                errors.append(f"Test {i+1}: Expected {expected}, got {result}")
        except Exception:
            errors.append(f"Test {i+1}: Runtime Error - {traceback.format_exc()}")
    
    if errors:
        return {"status": "error", "error": "; ".join(errors)}
    
    return {"status": "success"}

if __name__ == "__main__":
    try:
        result = run_tests()
        print(json.dumps(result))
    except Exception:
        print(json.dumps({"status": "error", "error": "Runner Crash:\n" + traceback.format_exc()}))
