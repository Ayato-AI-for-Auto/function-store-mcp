import ast
import logging
from typing import List, Set

logger = logging.getLogger(__name__)


class DependencySolver:
    """Detects required packages from Python source code using AST."""

    # Map of common import names to package names if they differ
    PACKAGE_MAP = {
        "cv2": "opencv-python",
        "PIL": "Pillow",
        "yaml": "PyYAML",
        "fastembed": "fastembed",
        "llama_cpp": "llama-cpp-python",
        "sklearn": "scikit-learn",
        "bs4": "beautifulsoup4",
        "skimage": "scikit-image",
    }

    @staticmethod
    def extract_imports(code: str) -> List[str]:
        """Extracts top-level package names from imports."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        packages: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    pkg = alias.name.split(".")[0]
                    packages.add(pkg)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    pkg = node.module.split(".")[0]
                    packages.add(pkg)

        # Standard library modules to ignore
        # This is a simplified list; in a real scenario, we might want a full stdlib list.
        std_lib = {
            "os",
            "sys",
            "re",
            "json",
            "ast",
            "datetime",
            "math",
            "collections",
            "typing",
            "logging",
            "tempfile",
            "subprocess",
            "base64",
            "hashlib",
            "abc",
            "functools",
            "inspect",
            "io",
            "pathlib",
            "random",
            "time",
            "threading",
            "queue",
            "socket",
            "struct",
            "traceback",
            "uuid",
            "xml",
        }

        # Filter and map
        final_packages = []
        for p in packages:
            if p in std_lib:
                continue
            # Map common names (cv2 -> opencv-python)
            mapped = DependencySolver.PACKAGE_MAP.get(p, p)
            final_packages.append(mapped)

        return sorted(list(set(final_packages)))

    @staticmethod
    def identify_internal_dependencies(
        code: str, known_functions: Set[str]
    ) -> List[str]:
        """Identifies calls to other functions already in the store."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        calls: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in known_functions:
                        calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    # Handle cases like math.sqrt (but we want local functions)
                    pass

        return sorted(list(calls))


if __name__ == "__main__":
    test_code = """
import os
import pandas as pd
from sklearn.model_selection import train_test_split
import cv2
from .local_module import test
    """
    print(f"Detected: {DependencySolver.extract_imports(test_code)}")
