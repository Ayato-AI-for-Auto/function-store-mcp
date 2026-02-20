import hashlib
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple

from mcp_core.core.config import DATA_DIR

logger = logging.getLogger(__name__)

# --- Warm Pool / Layered Environments ---
BASE_ENV_CONFIGS = {
    "data-science": ["numpy", "pandas", "scipy", "scikit-learn", "matplotlib"],
    "web-scraping": ["requests", "beautifulsoup4", "httpx", "lxml"],
}


class EnvManager:
    """
    Manages shared virtual environments based on dependency hashes.
    Ensures zero duplication of environments with the same libraries.
    """

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir

    def _are_deps_available(self, dependencies: List[str]) -> bool:
        """Check if all dependencies are available in the current environment."""
        import importlib.util

        for d in dependencies:
            name = (
                d.split("==")[0]
                .split(">=")[0]
                .split("<")[0]
                .strip()
                .lower()
                .replace("-", "_")
            )
            if importlib.util.find_spec(name) is None:
                return False
        return True

    def get_python_executable(self, dependencies: List[str]) -> Tuple[str, str]:
        """
        Returns the path to the python executable for the given dependencies.
        """
        if not dependencies:
            return sys.executable, ""

        if self._are_deps_available(dependencies):
            logger.debug(f"EnvManager: Dependencies {dependencies} met by inheritance.")
            return sys.executable, ""

        requested_set = set(
            d.split("==")[0].split(">=")[0].strip().lower() for d in dependencies
        )
        for name, deps in BASE_ENV_CONFIGS.items():
            base_set = set(deps)
            if requested_set.issubset(base_set):
                logger.debug(f"EnvManager: Match found in Warm Pool -> '{name}'")
                deps_str = "|".join(sorted(deps))
                env_hash = (
                    f"base_{name}_{hashlib.sha256(deps_str.encode()).hexdigest()[:8]}"
                )
                env_path = self.root_dir / env_hash
                python_exe = env_path / (
                    "Scripts/python.exe" if os.name == "nt" else "bin/python"
                )

                if python_exe.exists():
                    return str(python_exe), ""

                logger.info(f"EnvManager: Initializing Base Environment '{name}'...")
                return self._create_env(env_path, deps)

        deps_str = "|".join(sorted([d.strip().lower() for d in dependencies]))
        env_hash = hashlib.sha256(deps_str.encode()).hexdigest()[:12]
        env_path = self.root_dir / env_hash
        python_exe = env_path / (
            "Scripts/python.exe" if os.name == "nt" else "bin/python"
        )

        if python_exe.exists():
            return str(python_exe), ""

        logger.info(
            f"EnvManager: Creating new environment for {dependencies} at {env_path}"
        )
        return self._create_env(env_path, dependencies)

    def _create_env(self, env_path: Path, dependencies: List[str]) -> Tuple[str, str]:
        """Core logic for venv creation and installation."""
        python_exe = env_path / (
            "Scripts/python.exe" if os.name == "nt" else "bin/python"
        )
        try:
            subprocess.run(
                ["uv", "venv", str(env_path)],
                check=True,
                capture_output=True,
                timeout=60,
            )
            install_cmd = [
                "uv",
                "pip",
                "install",
                "--python",
                str(python_exe),
            ] + dependencies
            process = subprocess.Popen(
                install_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )

            logger.info(f"EnvManager: Installation started for {dependencies}...")
            full_log = []
            start_time = time.time()
            timeout = 600

            while True:
                if process.stdout is None:
                    break
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    clean_line = line.strip()
                    if clean_line:
                        logger.info(f"[uv-install] {clean_line}")
                        full_log.append(clean_line)
                if time.time() - start_time > timeout:
                    process.terminate()
                    shutil.rmtree(env_path, ignore_errors=True)
                    return (
                        "",
                        f"Install Timeout: Dependency installation took longer than {timeout}s.",
                    )

            if process.returncode != 0:
                shutil.rmtree(env_path, ignore_errors=True)
                return "", f"Install Failed (Code {process.returncode}):\n" + "\n".join(
                    full_log
                )
            return str(python_exe), ""
        except Exception as e:
            shutil.rmtree(env_path, ignore_errors=True)
            return "", f"Env Creation Error: {str(e)}"

    def capture_freeze(self, python_exe: str) -> List[str]:
        """Runs uv pip freeze in the specified environment to capture exact versions."""
        try:
            logger.info(f"EnvManager: Running capture_freeze using {python_exe}")
            # Use uv pip freeze for better performance and consistency
            result = subprocess.run(
                ["uv", "pip", "freeze", "--python", python_exe],
                capture_output=True,
                text=True,
                check=True,
            )
            output = [
                line.strip() for line in result.stdout.splitlines() if line.strip()
            ]
            logger.info(
                f"EnvManager: Captured {len(output)} packages via uv pip freeze."
            )
            return output
        except Exception as e:
            logger.error(f"EnvManager: Failed to capture freeze: {e}")
            return []


# Docker remains removed in runtime consolidation phase.

_envs_dir = DATA_DIR / ".mcp_envs"
_envs_dir.mkdir(parents=True, exist_ok=True)
env_manager = EnvManager(_envs_dir)
