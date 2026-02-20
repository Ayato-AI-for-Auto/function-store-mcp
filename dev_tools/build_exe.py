import os
import shutil
import subprocess
from pathlib import Path


def build():
    project_root = Path(__file__).parent.parent.resolve()
    os.chdir(project_root)

    print(f"Building FunctionStore.exe in {project_root}...")

    # Clean old builds
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            print(f"Cleaning {folder}...")
            shutil.rmtree(folder)

    # Run PyInstaller
    try:
        subprocess.run(["pyinstaller", "--noconfirm", "FunctionStore.spec"], check=True)
        print(
            "\n[SUCCESS] Build complete! You can find the executable in the 'dist' folder."
        )

        # Optionally, move to a 'release' folder
        release_dir = project_root / "release"
        release_dir.mkdir(exist_ok=True)
        shutil.copy(
            project_root / "dist" / "FunctionStore.exe",
            release_dir / "FunctionStore.exe",
        )
        print(f"Copied to {release_dir / 'FunctionStore.exe'}")

    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Build failed: {e}")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")


if __name__ == "__main__":
    build()
