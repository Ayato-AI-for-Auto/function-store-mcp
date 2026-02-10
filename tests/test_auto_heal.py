import os
import sys
import logging
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))

from solo_mcp.quality_gate import QualityGate  # noqa: E402

# Set up basic logging to see the heal attempts
logging.basicConfig(level=logging.INFO)

def test_auto_heal_flow():
    print("=== Auto-Heal Unit Test ===")
    gate = QualityGate()
    
    name = "image_resizer"
    code = """
from PIL import Image
def resize_image(path: str, width: int, height: int):
    img = Image.open(path)
    return img.resize((width, height))
"""
    
    # Test Case 1: Poor initial description -> Should be healed
    print("\n[Test 1] Testing Auto-Heal with poor initial description...")
    desc_poor = "resize image" # Very minimal
    
    report = gate.check_with_heal(name, code, desc_poor, desc_poor, max_retries=2)
    
    print(f"Status: {report['status']}")
    print(f"Score: {report['score']}/100")
    print(f"Heal Attempts: {report['heal_attempts']}")
    
    if report['healed_desc_en']:
        print(f"Healed EN: {report['healed_desc_en']}")
        print(f"Healed JP: {report['healed_desc_jp']}")
    else:
        print("No heal was applied (already passed or failed).")

    # Test Case 2: Code quality failure -> Should NOT attempt heal
    print("\n[Test 2] Testing code quality failure (should block heal)...")
    code_bad = "def bad_func(: return 1" # Syntax error
    
    report_bad = gate.check_with_heal("bad_func", code_bad, "Fix this", "修正して", max_retries=2)
    print(f"Status: {report_bad['status']}")
    print(f"Heal Attempts: {report_bad['heal_attempts']}") # Should be 0

if __name__ == "__main__":
    if not os.environ.get("GOOGLE_API_KEY"):
        print("ERROR: GOOGLE_API_KEY is required for this test.")
        sys.exit(1)
        
    try:
        test_auto_heal_flow()
        print("\n=== Auto-Heal Test Sequence Completed ===")
    except Exception as e:
        print(f"\nFATAL ERROR during test: {e}")
        sys.exit(1)
