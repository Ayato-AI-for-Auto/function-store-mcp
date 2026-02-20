import json
import logging
import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SecurityAuditService:
    """
    Security Audit Service using Bandit (static) and Safety (dependency check).
    """

    @staticmethod
    def _get_bin(name: str) -> str:
        """Find the binary for a tool."""
        import sys

        bin_dir = "Scripts" if os.name == "nt" else "bin"

        # 1. Try sys.prefix
        prefix_bin = os.path.join(sys.prefix, bin_dir, name)
        if os.name == "nt" and not prefix_bin.lower().endswith(".exe"):
            prefix_bin += ".exe"
        if os.path.exists(prefix_bin):
            return prefix_bin

        # 2. Standard lookup
        found = shutil.which(name)
        if found:
            return found

        return name

    @classmethod
    def run_bandit(cls, code: str) -> Dict[str, Any]:
        """Runs Bandit static analysis on a code snippet."""
        result = {"passed": True, "findings": [], "score_penalty": 0}

        with tempfile.NamedTemporaryFile(
            suffix=".py", delete=False, mode="w", encoding="utf-8"
        ) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            bandit_bin = cls._get_bin("bandit")
            # Run Bandit
            # -f json: Output format
            # -q: Quiet mode
            process = subprocess.run(
                [bandit_bin, "-f", "json", "-q", tmp_path],
                capture_output=True,
                text=True,
                encoding="utf-8",
                shell=os.name == "nt",
            )

            # Bandit returns non-zero if findings are found (with different levels)
            if not process.stdout.strip():
                return result

            data = json.loads(process.stdout)
            findings = data.get("results", [])
            for f in findings:
                severity = f.get("issue_severity", "LOW")
                confidence = f.get("issue_confidence", "LOW")
                msg = f.get("issue_text", "Unknown issue")
                line = f.get("line_number", "?")

                result["findings"].append(f"Line {line} [{severity}]: {msg}")

                # Penalty based on severity
                if severity == "HIGH":
                    result["score_penalty"] += 40
                elif severity == "MEDIUM":
                    result["score_penalty"] += 20
                else:
                    result["score_penalty"] += 5

            if result["score_penalty"] > 0:
                result["passed"] = False
                result["score_penalty"] = min(
                    result["score_penalty"], 80
                )  # Max 80 penalty

        except Exception as e:
            logger.error(f"Bandit execution failed: {e}")
            # Do not penalize if the tool itself fails to run
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        return result

    @classmethod
    def run_safety(cls, dependencies: List[str]) -> Dict[str, Any]:
        """Runs Safety check on a list of dependencies."""
        result = {"passed": True, "findings": [], "score_penalty": 0}
        if not dependencies:
            return result

        # Create a temporary requirements.txt
        with tempfile.NamedTemporaryFile(
            suffix=".txt", delete=False, mode="w", encoding="utf-8"
        ) as tmp:
            for dep in dependencies:
                tmp.write(f"{dep}\n")
            tmp_path = tmp.name

        try:
            safety_bin = cls._get_bin("safety")
            # Run Safety check
            # check -r: requirements file
            # --json: output format
            process = subprocess.run(
                [safety_bin, "check", "-r", tmp_path, "--json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                shell=os.name == "nt",
            )

            if not process.stdout.strip():
                return result

            # Safety output format can vary, but usually it's a list or dict
            data = json.loads(process.stdout)
            # Vulnerabilities are often in a 'vulnerabilities' key or just top level
            vulns = data if isinstance(data, list) else data.get("vulnerabilities", [])

            for v in vulns:
                # Format: [package, version, current_version, description, id]
                # Safety 2.0+ format is more structured
                if isinstance(v, dict):
                    pkg = v.get("package_name", "unknown")
                    v_id = v.get("vulnerability_id", "unknown")
                    msg = v.get("advisory", "Security vulnerability detected")
                else:
                    pkg = v[0]
                    v_id = v[4]
                    msg = v[3]

                result["findings"].append(f"Dependency [{pkg}] (ID: {v_id}): {msg}")
                result["score_penalty"] += 30  # Harsh penalty for vulnerable deps

            if result["score_penalty"] > 0:
                result["passed"] = False
                result["score_penalty"] = min(result["score_penalty"], 90)

        except Exception as e:
            # Safety might not be installed or need auth in 2.0+
            # We treat failure to run as a skip for now
            logger.warning(f"Safety execution failed or not installed: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        return result
