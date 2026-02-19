import ast
import re
from typing import Tuple

# --- Security Patterns ---
SECRET_PATTERNS = [
    r"AIza[0-9A-Za-z_-]{35}",  # Google API Key
    r"ghp_[a-zA-Z0-9]{36}",  # GitHub Personal Access Token
]


class ASTSecurityChecker:
    """
    Static analysis to detect potentially dangerous code.
    Policy: PERMISSIVE - Allow most operations, but block obviously malicious ones.
    """

    FORBIDDEN_CALLS = {
        "os": {"fork", "kill", "setuid", "setgid", "chroot", "system"},
        "pty": {"spawn"},
        "subprocess": {
            "run",
            "Popen",
            "call",
            "check_call",
            "check_output",
        },  # Closely monitored
        "builtins": {"eval", "exec"},
    }

    @classmethod
    def check(cls, code: str) -> Tuple[bool, str]:
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # 1. Handle attribute calls: os.system(), subprocess.run()
                    if isinstance(node.func, ast.Attribute):
                        if isinstance(node.func.value, ast.Name):
                            module_alias = node.func.value.id
                            method_name = node.func.attr
                            if module_alias in cls.FORBIDDEN_CALLS:
                                if method_name in cls.FORBIDDEN_CALLS[module_alias]:
                                    return (
                                        False,
                                        f"Security Block: '{module_alias}.{method_name}' is forbidden.",
                                    )

                    # 2. Handle direct name calls: eval(), exec()
                    elif isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        # Check against known dangerous globals
                        if func_name in {"eval", "exec", "system", "fork"}:
                            return (
                                False,
                                f"Security Block: Direct call to '{func_name}' is forbidden.",
                            )
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
