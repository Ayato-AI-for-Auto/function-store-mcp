from mcp_core.engine.quality_gate import RuffProcessor


def test_valid_code_passes():
    code = "def hello():\n    return 'world'"
    passed, errors = RuffProcessor.lint(code)
    assert passed is True
    assert len(errors) == 0


def test_syntax_error_fails():
    code = "def broken_func(: return 1"
    passed, errors = RuffProcessor.lint(code)
    assert passed is False
    assert len(errors) > 0
    assert any(
        "SyntaxError" in err or "Expected" in err or "Line 1" in err for err in errors
    )


def test_unused_import_fails():
    code = "import os\ndef hello():\n    return 'hi'"
    passed, errors = RuffProcessor.lint(code)
    assert passed is False
    assert len(errors) > 0
    assert any("F401" in err or "unused" in err.lower() for err in errors)


def test_empty_code():
    passed, errors = RuffProcessor.lint("")
    assert passed is True
    assert len(errors) == 0
