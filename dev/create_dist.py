import os
import shutil
from pathlib import Path

def create_dist():
    # Assume running from Project Root
    root_dir = Path(os.getcwd())
    print(f"=== Creating Distribution Package (Root: {root_dir}) ===")
    
    dist_dir = root_dir / "dist_package"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir()

    # Create subdirectories
    utils_dir = dist_dir / "utils"
    utils_dir.mkdir()
    
    scripts_dir = dist_dir / "scripts"
    scripts_dir.mkdir()

    # 1. Root Files (Clean Entry Point)
    root_files = [
        ("FunctionStore.bat", "FunctionStore.bat"),
        ("README.md", "README.md"),
        ("pyproject.toml", "pyproject.toml"),
        ("ROADMAP.md", "ROADMAP.md"),
        ("Dockerfile", "Dockerfile"),
    ]

    # 2. Utils (Hidden implementation details)
    # Note: setup_windows.bat is now assumed to be in utils/ in the dist package
    utils_files = [
        ("utils/setup_windows.bat", "setup_windows.bat"),
        ("utils/start_server.bat", "start_server.bat"),
        ("utils/start_api.bat", "start_api.bat"),
        ("utils/start_hidden.vbs", "start_hidden.vbs"),
    ]
    
    # 3. Scripts (Python logic)
    scripts_files = [
        ("scripts/configure_claude.py", "configure_claude.py"),
        ("scripts/verify_setup.py", "verify_setup.py"),
        ("scripts/launcher.py", "launcher.py"),
        ("scripts/install_torch.py", "install_torch.py"),
    ]
    
    # 4. Source Dir
    dirs_to_copy = [
        ("function_store_mcp", "function_store_mcp"),
        ("docker", "docker")
    ]

    # --- Copy Operations ---

    # Copy Root Files
    for src, dst in root_files:
        src_path = root_dir / src
        if src_path.exists():
            shutil.copy2(src_path, dist_dir / dst)
            print(f"Copied to ROOT: {src}")
        else:
            print(f"[WARN] File not found: {src}")

    # Copy Utils
    for src, dst in utils_files:
        src_path = root_dir / src
        if src_path.exists():
            shutil.copy2(src_path, utils_dir / dst)
            print(f"Copied to UTILS: {src}")
        else:
            print(f"[WARN] Utils file not found: {src}")

    # Copy Scripts
    for src, dst in scripts_files:
        src_path = root_dir / src
        if src_path.exists():
            shutil.copy2(src_path, scripts_dir / dst)
            print(f"Copied to SCRIPTS: {src}")
        else:
            print(f"[WARN] Script not found: {src}")

    # Copy Source Dir
    for src, dst in dirs_to_copy:
        src_path = root_dir / src
        dst_path = dist_dir / dst
        if src_path.exists():
            shutil.copytree(src_path, dst_path)
            print(f"Copied directory: {src}")

    print("")
    print("========================================")
    print("SUCCESS: Distribution package created.")
    print("Location: dist_package")
    print("========================================")

if __name__ == "__main__":
    create_dist()