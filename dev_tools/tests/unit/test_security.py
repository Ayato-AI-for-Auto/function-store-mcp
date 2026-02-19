from mcp_core.core.security import ASTSecurityChecker, _contains_secrets


def test_safe_code():
    code = "def add(a, b): return a + b"
    is_safe, msg = ASTSecurityChecker.check(code)
    assert is_safe is True
    assert msg == ""


def test_os_system_blocked():
    code = "import os\ndef evil(): os.system('rm -rf /')"
    is_safe, msg = ASTSecurityChecker.check(code)
    assert is_safe is False
    assert "os.system" in msg


def test_os_fork_blocked():
    code = "import os\ndef evil(): os.fork()"
    is_safe, msg = ASTSecurityChecker.check(code)
    assert is_safe is False
    assert "os.fork" in msg


def test_subprocess_run_blocked():
    code = "import subprocess\ndef evil(): subprocess.run(['ls'])"
    is_safe, msg = ASTSecurityChecker.check(code)
    assert is_safe is False
    assert "subprocess.run" in msg


def test_eval_blocked():
    # builtins.eval is typically used via names like 'eval' directly or __builtins__.eval
    # Our current AST checker looks for module_alias.method_name.
    # Let's see if it handles direct 'eval' or needs explicit module.
    code = "eval('1+1')"
    # Currently ASTSecurityChecker.check only looks for Attrib calls (module.func).
    # We might want to improve the checker to handle Name calls (direct eval).
    # But let's test current implementation first.
    is_safe, msg = ASTSecurityChecker.check(code)
    assert is_safe is False
    assert "eval" in msg

    code_explicit = "import builtins\nbuiltins.eval('1+1')"
    is_safe, msg = ASTSecurityChecker.check(code_explicit)
    assert is_safe is False
    assert "eval" in msg


def test_secret_google_api_key():
    code = "API_KEY = 'AIzaSyD-1234567890abcdefghijklmnopqrstuvw'"
    has_secret, secret = _contains_secrets(code)
    assert has_secret is True
    assert "AIza" in secret


def test_secret_github_token():
    # ghp_ followed by 36 characters
    code = "TOKEN = 'ghp_abcdefghijklmnopqrstuvwxyz0123456789abc'"
    has_secret, secret = _contains_secrets(code)
    assert has_secret is True
    assert "ghp_" in secret


def test_no_false_positive():
    code = "def my_func(): return 'Just a normal string'"
    has_secret, secret = _contains_secrets(code)
    assert has_secret is False
    assert secret == ""
