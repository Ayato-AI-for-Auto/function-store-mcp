import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))

from solo_mcp.sanitizer import DataSanitizer  # noqa: E402

def test_sanitizer():
    print("=== Data Sanitizer Unit Test ===")
    
    # Test 1: Full-width spaces and Emojis in metadata
    print("\n[Test 1] Metadata Cleaning...")
    input_text = "文字化けテスト　🚀✨🌟　半角にします"
    # expected = "文字化けテスト  半角にします"
    cleaned = DataSanitizer.clean_text(input_text)
    print(f"Input:    '{input_text}'")
    print(f"Cleaned:  '{cleaned}'")
    assert "🚀" not in cleaned
    assert "✨" not in cleaned
    assert "\u3000" not in cleaned # No full-width space

    # Test 2: Code Emoji Stripping
    print("\n[Test 2] Code Cleaning (Removing Emojis from Literals)...")
    input_code = """
def test_func():
    \"\"\"This is a 🚀 test docstring.\"\"\"
    print("Log: ✅ Success ✨") # This should be cleaned
    return True
"""
    cleaned_code = DataSanitizer.clean_code(input_code)
    print("--- Cleaned Code ---")
    print(cleaned_code)
    print("--------------------")
    assert "🚀" not in cleaned_code
    assert "✅" not in cleaned_code
    assert "✨" not in cleaned_code

    # Test 3: Batch Sanitize
    print("\n[Test 3] Batch Sanitize...")
    data = DataSanitizer.sanitize(
        name="test_🚀_func",
        code="print('Hi 🌟')",
        description="Cool 💎 tool",
        tags=["ai", "🚀"],
        desc_en="English 🇺🇸",
        desc_jp="日本語 🇯🇵"
    )
    print(f"Sanitized Name: {data['name']}")
    print(f"Sanitized Tags: {data['tags']}")
    assert data['name'] == "test_func"
    assert len(data['tags']) == 1 # Only 'ai' remains, '🚀' becomes empty and filtered
    assert "ai" in data['tags']

    print("\n[SUCCESS] All Sanitizer checks passed.")

if __name__ == "__main__":
    try:
        test_sanitizer()
    except AssertionError as e:
        print(f"\n[FAILED] Assertion Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL] Error: {e}")
        sys.exit(1)
