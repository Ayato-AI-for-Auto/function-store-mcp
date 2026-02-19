import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

from mcp_core.core.security import ASTSecurityChecker
from mcp_core.runtime.environment import env_manager

logger = logging.getLogger(__name__)


class SubprocessRuntime:
    """
    Robust Subprocess Runtime with pooling and timeout.
    """

    def run_function(
        self, code: str, test_cases: List[Dict], python_exe: str
    ) -> Tuple[bool, str]:
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runner_code = self._create_runner_script(code, test_cases)
            runner_path = temp_path / "runner.py"
            runner_path.write_text(runner_code, encoding="utf-8")
            env = os.environ.copy()
            try:
                result = subprocess.run(
                    [python_exe, str(runner_path)],
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=30,
                )
                if result.returncode != 0:
                    return (
                        False,
                        f"Execution Error (Code {result.returncode}):\n{result.stderr or result.stdout}",
                    )
                try:
                    output = json.loads(result.stdout.strip().splitlines()[-1])
                    if output.get("status") == "success":
                        return True, ""
                    else:
                        return False, output.get("error", "Unknown error")
                except (json.JSONDecodeError, IndexError):
                    return False, f"Invalid runner output: {result.stdout}"
            except subprocess.TimeoutExpired:
                return False, "Execution Timed Out (30s)"
            except Exception as e:
                return False, f"Runtime Exception: {str(e)}"

    def _create_runner_script(self, code: str, test_cases: List[Dict]) -> str:
        return f"""
import json
import traceback

def run():
    namespace = {{}}
    try:
        exec({repr(code)}, namespace)
    except Exception:
        return {{"status": "error", "error": "Compilation/Setup Error:\\n" + traceback.format_exc()}}
    
    candidates = [v for k, v in namespace.items() if callable(v) and not k.startswith('_')]
    if not candidates:
        return {{"status": "error", "error": "No function found in code."}}
    func = candidates[-1]

    test_cases = {json.dumps(test_cases)}
    errors = []
    for i, tc in enumerate(test_cases):
        try:
            res = func(**tc.get('input', {{}}))
            if res != tc.get('expected'):
                errors.append(f"Test {{i+1}}: Expected {{tc.get('expected')}}, got {{res}}")
        except Exception:
            errors.append(f"Test {{i+1}}: Runtime Error - " + traceback.format_exc())
    
    if errors:
        return {{"status": "error", "error": "; ".join(errors)}}
    return {{"status": "success"}}

if __name__ == "__main__":
    print(json.dumps(run()))
"""


subprocess_runtime = SubprocessRuntime()


def _run_test_cases(
    code: str, test_cases: List[Dict], dependencies: List[str] = []
) -> Tuple[bool, str]:
    """Unified entry point for running tests with dependency isolation."""
    is_safe, msg = ASTSecurityChecker.check(code)
    if not is_safe:
        return False, f"Security Block: {msg}"

    # Get isolated environment
    python_exe, err = env_manager.get_python_executable(dependencies)
    if err:
        return False, f"Environment Error: {err}"

    return subprocess_runtime.run_function(code, test_cases, python_exe)
