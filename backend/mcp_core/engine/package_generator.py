import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

MANAGED_MARKER = "# [FUNCTION-STORE-MANAGED]"


class PackageGenerator:
    """
    Handles generation and maintenance of local_pkg/ for Smart Module Injection.
    """

    @staticmethod
    def inject_package(target_root: str, functions: List[Dict]) -> str:
        """
        Injects a set of functions into target_root/local_pkg/.
        Each function in 'functions' should contain 'name' and 'code'.
        """
        try:
            target_path = Path(target_root) / "local_pkg"
            target_path.mkdir(parents=True, exist_ok=True)

            # 1. Export each function file
            exported_names = []
            for func in functions:
                f_name = func["name"]
                f_code = func["code"]

                file_path = target_path / f"{f_name}.py"

                # Check for existing file and markers
                should_write = True
                if file_path.exists():
                    content = file_path.read_text(encoding="utf-8")
                    if MANAGED_MARKER not in content:
                        logger.warning(
                            f"File {file_path} exists but is NOT managed. Skipping to avoid overwriting user changes."
                        )
                        should_write = False

                if should_write:
                    # Prepend marker if not present in the code from store
                    final_code = f_code
                    if MANAGED_MARKER not in final_code:
                        final_code = f"{MANAGED_MARKER}\n{final_code}"

                    file_path.write_text(final_code, encoding="utf-8")
                    exported_names.append(f_name)

            # 2. Update __init__.py
            PackageGenerator._update_init_py(target_path, exported_names)

            return f"Successfully injected {len(exported_names)} functions into {target_path}"
        except Exception as e:
            logger.error(f"Injection failed: {e}")
            return f"Error during injection: {str(e)}"

    @staticmethod
    def _update_init_py(package_path: Path, func_names: List[str]):
        """
        Incremental merge of imports into __init__.py.
        """
        init_file = package_path / "__init__.py"
        existing_content = ""
        if init_file.exists():
            existing_content = init_file.read_text(encoding="utf-8")

        new_lines = []
        if not existing_content:
            new_lines.append(MANAGED_MARKER)
            new_lines.append("# This package is managed by Function Store.\n")

        for name in func_names:
            import_line = f"from .{name} import {name}"
            # Check if already imported
            # Simple check, could be improved with AST but usually fine for MVP
            if import_line not in existing_content:
                new_lines.append(import_line)

        if new_lines:
            # If init file exists, append new imports at the end
            if existing_content:
                updated_content = (
                    existing_content.rstrip() + "\n" + "\n".join(new_lines) + "\n"
                )
            else:
                updated_content = "\n".join(new_lines) + "\n"

            init_file.write_text(updated_content, encoding="utf-8")
