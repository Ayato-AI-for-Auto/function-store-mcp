import ast
import re
from typing import Tuple

# --- Security Patterns ---
SECRET_PATTERNS = [
    r'AIza[0-9A-Za-z_-]{35}',         # Google API Key
    r'ghp_[a-zA-Z0-9]{36}',           # GitHub Personal Access Token
]

class ASTSecurityChecker:
    """
    Static analysis to detect potentially dangerous code.
    Policy: PERMISSIVE - Allow most operations, but block obviously malicious ones.
    """
    FORBIDDEN_CALLS = {
        'os': {'fork', 'kill', 'setuid', 'setgid', 'chroot'},
        'pty': {'spawn'},
        'subprocess': {}, # Allow subprocess, but monitor logs
    }

    @classmethod
    def check(cls, code: str) -> Tuple[bool, str]:
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if isinstance(node.func.value, ast.Name):
                            module_alias = node.func.value.id
                            method_name = node.func.attr
                            if module_alias in cls.FORBIDDEN_CALLS:
                                if method_name in cls.FORBIDDEN_CALLS[module_alias]:
                                    return False, f"Security Block: '{module_alias}.{method_name}' is forbidden."
            return True, ""
        except SyntaxError as e:
            return False, f"Syntax Error: {e}"

def _contains_secrets(code: str) -> Tuple[bool, str]:
    """Scans code for potential API keys or secrets using regex."""
    for pattern in SECRET_PATTERNS:
        matches = re.findall(pattern, code)
        if matches:
            return True, matches[0]
    return False, ""
