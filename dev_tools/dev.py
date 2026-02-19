import argparse
import logging
import os
import subprocess
import sys
import time
import traceback


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("dev_tool.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def run_command(cmd, name):
    print(f"\n[INFO] Running {name}...")
    start = time.time()
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        # Use capture_output=False to let it stream to terminal
        cp = subprocess.run(cmd, shell=True, capture_output=False, cwd=root_dir)
    except Exception as e:
        print(f"[ERROR] Unexpected error running command '{cmd}': {e}")
        return False

    elapsed = time.time() - start
    if cp.returncode == 0:
        print(f"[SUCCESS] {name} completed in {elapsed:.2f}s")
    else:
        print(f"[FAIL] {name} failed with exit code {cp.returncode}")
    return cp.returncode == 0


def main():
    setup_logging()
    try:
        parser = argparse.ArgumentParser(description="Horiemon-approved Developer Tool")
        parser.add_argument("--test-only", action="store_true", help="Run only tests")
        parser.add_argument("--lint-only", action="store_true", help="Run only lint")
        parser.add_argument("--ship", action="store_true", help="CI + git push")
        parser.add_argument(
            "-m", "--message", type=str, help="Commit message for --ship"
        )
        parser.add_argument("--publish", type=str, help="Publish a function to the Hub")
        parser.add_argument(
            "--publish-all",
            action="store_true",
            help="Publish ALL functions to the Hub",
        )
        args = parser.parse_args()

        # Always clean garbage first
        clean_garbage()

        # Handle Sync Publish (Special Case, doesn't require full CI)
        if args.publish or args.publish_all:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
            from mcp_core.engine.sync_engine import sync_engine

            if args.publish_all:
                print("[INFO] Publishing ALL local functions to Hub...")
                sync_engine.publish_all()
            else:
                print(f"[INFO] Publishing '{args.publish}' to Hub...")
                if sync_engine.push(args.publish):
                    print(f"[SUCCESS] '{args.publish}' published successfully.")
                else:
                    print(f"[FAIL] Failed to publish '{args.publish}'.")
            sys.exit(0)

        success = True

        if not args.test_only:
            # 1. Ruff Check
            if not run_command("uv run --no-sync ruff check --fix", "Ruff Lint & Fix"):
                success = False

            # 2. Ruff Format
            if not run_command("uv run --no-sync ruff format", "Ruff Format"):
                success = False

        if not args.lint_only:
            # 3. Pytest
            pytest_cmd = (
                os.path.normpath(".venv/Scripts/python.exe")
                + " -m pytest dev_tools/tests"
            )
            if not run_command(pytest_cmd, "Pytest"):
                success = False

        if success:
            print("\n" + "=" * 40)
            print("  ALL CLEAR. YOU'RE DOING GOOD.  ")
            print("=" * 40)

            if args.ship:
                msg = args.message or "chore: ship via dev_tools"
                print(f"\n[INFO] Shipping: {msg}...")
                if run_command("git add -A", "Git Add"):
                    if run_command(f'git commit -m "{msg}"', "Git Commit"):
                        run_command("git push origin main", "Git Push")
        else:
            print("\n" + "!" * 40)
            print("  SOME TASKS FAILED. FIX THEM.  ")
            print("!" * 40)
            sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error occurred: {e}")
        logging.error(traceback.format_exc())
        print(f"\n[CRITICAL] Unexpected error: {e}")
        sys.exit(1)


def clean_garbage():
    """Remove .txt and .log files from the project root."""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    count = 0
    error_count = 0
    print(f"\n[INFO] Horiemon Cleanup: Scanning {root_dir}...")

    for filename in os.listdir(root_dir):
        if filename.endswith(".txt") or filename.endswith(".log"):
            filepath = os.path.join(root_dir, filename)
            try:
                os.remove(filepath)
                print(f"  [DELETE] Garbage file: {filename}")
                count += 1
            except PermissionError:
                logging.warning(f"Permission denied: Could not delete {filename}")
                print(f"  [WARNING] Permission denied: Could not delete {filename}")
                error_count += 1
            except Exception as e:
                logging.error(f"Unexpected error deleting {filename}: {e}")
                logging.error(traceback.format_exc())
                print(f"  [ERROR] Unexpected error deleting {filename}: {e}")
                error_count += 1

    if count > 0:
        print(f"[SUCCESS] Deleted {count} garbage files.")
    elif error_count > 0:
        print(f"[WARNING] Encountered {error_count} errors during cleanup.")
    else:
        print("[INFO] No garbage found. Clean.")


if __name__ == "__main__":
    main()
