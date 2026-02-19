import time

from mcp_core.core.database import get_db_connection
from mcp_core.engine.logic import do_save_impl


def test_save_valid_function():
    ts = int(time.time())
    name = f"valid_func_{ts}"
    code = 'def hello() -> str:\n    """Returns hello."""\n    return \'hello\''
    res = do_save_impl(asset_name=name, code=code, description="Valid")
    assert "SUCCESS" in res

    # Verify in DB
    conn = get_db_connection()
    row = conn.execute(
        "SELECT status FROM functions WHERE name = ?", (name,)
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "pending"


def test_save_syntax_error_rejected():
    ts = int(time.time())
    res = do_save_impl(
        asset_name=f"syntax_error_{ts}",
        code="def broken_func(: return 1",
        description="Broken",
    )
    assert "REJECTED" in res
    assert "Syntax Error" in res


def test_save_security_violation_rejected():
    ts = int(time.time())
    res = do_save_impl(
        asset_name=f"security_evil_{ts}",
        code="import os\ndef evil(): os.system('rm -rf /')",
        description="Evil",
    )
    assert "REJECTED" in res
    assert "Security Block" in res


def test_save_secret_leak_rejected():
    ts = int(time.time())
    res = do_save_impl(
        asset_name=f"secret_leak_{ts}",
        code="API_KEY = 'AIzaSyD-1234567890abcdefghijklmnopqrstuvw'",
        description="Leak",
    )
    assert "REJECTED" in res
    assert "Secret detected" in res


def test_save_lint_error_passed_with_background_scoring():
    ts = int(time.time())
    # Unused import causes Ruff to fail, but it should PASS the initial save gate
    res = do_save_impl(
        asset_name=f"lint_fail_{ts}",
        code="import math\ndef hello(): return 'hi'",
        description="Lint fail",
    )
    # This should now be SUCCESS because lint errors are processed in background
    assert "SUCCESS" in res


def test_save_skip_test_bypasses_lint_but_not_security():
    ts = int(time.time())
    name = f"security_blocked_even_with_skip_{ts}"
    # This code is malicious (os.system)
    code = "import os\ndef evil(): os.system('rm -rf /')"
    res = do_save_impl(
        asset_name=name, code=code, description="Evil bypass attempt", skip_test=True
    )
    # This should now be REJECTED despite skip_test=True
    assert "REJECTED" in res
    assert "Security Block" in res


def test_save_skip_test_success_with_lint_fail():
    ts = int(time.time())
    name = f"lint_bypassed_func_{ts}"
    # This code has a lint error (unused variable 'x') but is safe
    code = "def hello():\n    x = 1\n    return 'hi'"
    res = do_save_impl(
        asset_name=name, code=code, description="Bypassed", skip_test=True
    )
    assert "SUCCESS" in res

    conn = get_db_connection()
    row = conn.execute(
        "SELECT status FROM functions WHERE name = ?", (name,)
    ).fetchone()
    conn.close()
    assert row[0] == "unverified"
