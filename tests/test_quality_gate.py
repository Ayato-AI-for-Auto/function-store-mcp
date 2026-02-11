import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))

from mcp_core.quality_gate import QualityGate  # noqa: E402

def test_quality_gate_flow():
    print("=== Quality Gate Unit Test ===")
    gate = QualityGate()
    
    # Test Case 1: High Quality Function
    print("\n[Test 1] Testing high-quality function...")
    code_good = """
def calculate_area(radius: float) -> float:
    \"\"\"Calculates the area of a circle given its radius.\"\"\"
    import math
    return math.pi * (radius ** 2)
"""
    name = "calculate_area"
    desc_en = "Calculate the area of a circle based on a provided radius."
    desc_jp = "半径に基づいて円の面積を計算します。"
    
    report_good = gate.check(name, code_good, desc_en, desc_jp)
    print(f"Status: {report_good['status']}")
    print(f"Score: {report_good['score']}/100")
    print(f"Semantic Feedback: {report_good['description']['feedback']}")
    
    # Test Case 2: Poor Description (Should Fail)
    print("\n[Test 2] Testing poor description (Garbage Data)...")
    desc_bad = "this is a test" # Too short, no keywords
    
    report_bad = gate.check(name, code_good, desc_bad, desc_bad)
    print(f"Status: {report_bad['status']}")
    print(f"Score: {report_bad['score']}/100")
    print(f"Semantic Feedback: {report_bad['description']['feedback']}")

    # Test Case 3: Syntax Error (Should Fail)
    print("\n[Test 3] Testing syntax error...")
    code_error = "def broken_func(: return 1"
    report_error = gate.check("broken_func", code_error, "Simple func", "簡単な関数")
    print(f"Status: {report_error['status']}")
    print(f"Linter Passed: {report_error['linter']['passed']}")

if __name__ == "__main__":
    # Ensure API Key is available for LLM tests
    if not os.environ.get("GOOGLE_API_KEY"):
        print("WARNING: GOOGLE_API_KEY not found in environment. LLM reviews will be skipped.")
    
    try:
        test_quality_gate_flow()
        print("\n=== Test Sequence Completed ===")
    except Exception as e:
        print(f"\nFATAL ERROR during test: {e}")
