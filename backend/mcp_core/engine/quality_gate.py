import json
import logging
import os
import shutil
import subprocess
from typing import Any, Dict, List, Tuple

from .security_audit import SecurityAuditService

logger = logging.getLogger(__name__)


class RuffProcessor:
    @staticmethod
    def _get_ruff_bin() -> str:
        """Find the ruff binary."""
        import sys

        # 1. Try sys.prefix (works if running inside venv)
        bin_dir = "Scripts" if os.name == "nt" else "bin"
        prefix_ruff = os.path.join(sys.prefix, bin_dir, "ruff")
        if os.name == "nt" and not prefix_ruff.lower().endswith(".exe"):
            prefix_ruff += ".exe"

        if os.path.exists(prefix_ruff):
            return prefix_ruff

        # 2. Standard lookup
        ruff_bin = shutil.which("ruff")
        if ruff_bin:
            return ruff_bin

        # 3. Local .venv fallback (project root)
        root_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        local_ruff = os.path.join(root_dir, ".venv", bin_dir, "ruff")
        if os.name == "nt" and not local_ruff.lower().endswith(".exe"):
            local_ruff += ".exe"
        if os.path.exists(local_ruff):
            return local_ruff

        return "ruff"  # Final fallback to PATH search anyway

    @staticmethod
    def lint(code: str) -> Tuple[bool, List[str]]:
        """Checks code using Ruff Linter via stdin."""
        try:
            ruff_bin = RuffProcessor._get_ruff_bin()
            # Run Ruff Check with stdin
            # "-" tells ruff to read from stdin
            # We use --stdin-filename to give it context (optional but good practice)
            result = subprocess.run(
                [
                    ruff_bin,
                    "check",
                    "-",
                    "--output-format=json",
                    "--stdin-filename",
                    "snippet.py",
                ],
                input=code,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=os.name == "nt",
            )

            if result.returncode == 0:
                return True, []

            errors = []
            try:
                if not result.stdout.strip():
                    if result.stderr:
                        errors.append(f"Ruff Error: {result.stderr.strip()}")
                else:
                    data = json.loads(result.stdout)
                    for item in data:
                        code_id = item.get("code", "UNKNOWN")
                        message = item.get("message", "Unknown error")
                        row = item.get("location", {}).get("row", "?")
                        errors.append(f"Line {row} [{code_id}]: {message}")
            except json.JSONDecodeError:
                lines = [
                    line.strip() for line in result.stdout.splitlines() if line.strip()
                ]
                errors.extend(lines)

            return False, errors

        except Exception as e:
            return False, [f"Ruff Lint Exception: {str(e)}"]

    @staticmethod
    def format_check(code: str) -> Tuple[bool, str]:
        """Checks code formatting using Ruff Formatter via stdin."""
        try:
            ruff_bin = RuffProcessor._get_ruff_bin()
            # Run Ruff Format (check mode) with stdin
            result = subprocess.run(
                [ruff_bin, "format", "--check", "-", "--stdin-filename", "snippet.py"],
                input=code,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=os.name == "nt",
            )

            if result.returncode == 0:
                return True, "Code is formatted correctly (Ruff)."
            else:
                return False, "Code requires formatting (Ruff)."

        except Exception as e:
            return False, f"Ruff Format Exception: {str(e)}"


class QualityGate:
    def __init__(self):
        self.processor = RuffProcessor()
        self.security_auditor = SecurityAuditService()

    def check_score_only(
        self,
        name: str,
        code: str,
        description: str = "",
        dependencies: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Ultra-fast quality check using ONLY Ruff.
        """
        report = {
            "status": "evaluated",
            "final_score": 100,
            "linter": {"passed": True, "errors": []},
            "formatter": {"passed": True, "feedback": ""},
        }

        # 1. Linter (Normalized by Error Density: errors / lines)
        l_pass, l_errs = self.processor.lint(code)
        report["linter"] = {"passed": l_pass, "errors": l_errs}

        # Calculate line count (min 1 to avoid ZeroDivision)
        line_count = max(code.count("\n") + 1, 1)
        error_density = len(l_errs) / line_count

        # Linter Penalty: Density-based scaling (max 70 points)
        # e.g., 1 error in 10 lines (10% density) -> 50 points penalty
        linter_penalty = min(error_density * 500, 70)

        # 2. Formatter (Flat 30 points penalty if fails)
        f_pass, f_msg = self.processor.format_check(code)
        report["formatter"] = {"passed": f_pass, "feedback": f_msg}
        formatter_penalty = 0 if f_pass else 30

        # 3. Security Audit (New Phase 6)
        s_bandit = self.security_auditor.run_bandit(code)
        s_safety = self.security_auditor.run_safety(dependencies or [])

        report["security"] = {"bandit": s_bandit, "safety": s_safety}
        security_penalty = s_bandit["score_penalty"] + s_safety["score_penalty"]

        final_score = max(
            0, 100 - linter_penalty - formatter_penalty - security_penalty
        )
        report["final_score"] = int(final_score)

        if final_score >= 80:
            report["reliability"] = "high"
        elif final_score >= 50:
            report["reliability"] = "medium"
        else:
            report["reliability"] = "low"

        return report
