from mcp_core.engine.sanitizer import DataSanitizer


def test_clean_text_basic():
    text = "  Hello   World  "
    assert DataSanitizer.clean_text(text) == "Hello World"


def test_clean_text_full_width_space():
    text = "文字化けテスト\u3000半角にします"
    assert " " in DataSanitizer.clean_text(text)
    assert "\u3000" not in DataSanitizer.clean_text(text)


def test_clean_text_emojis():
    text = "Happy 🚀 Day! ✨"
    cleaned = DataSanitizer.clean_text(text)
    assert "🚀" not in cleaned
    assert "✨" not in cleaned
    assert cleaned == "Happy Day!"


def test_clean_code_emojis():
    code = "def test():\n    # 🚀 Rocket command\n    return '✅ OK'"
    cleaned = DataSanitizer.clean_code(code)
    assert "🚀" not in cleaned
    assert "✅" not in cleaned
    assert "#  Rocket command" in cleaned


def test_sanitize_batch():
    data = DataSanitizer.sanitize(
        name="test_🚀_func",
        code="print('Hi 🌟')",
        description="Cool 💎 tool",
        tags=["ai", "🚀"],
        desc_en="English 🇺🇸",
        desc_jp="日本語 🇯🇵",
    )
    assert data["name"] == "test_func"
    assert data["tags"] == ["ai"]
    assert "🚀" not in data["description"]
    assert "🇺🇸" not in data["description_en"]
    assert "🇯🇵" not in data["description_jp"]


def test_empty_inputs():
    res = DataSanitizer.sanitize("", "", "", [])
    assert res["name"] == ""
    assert res["code"] == ""
    assert res["tags"] == []
