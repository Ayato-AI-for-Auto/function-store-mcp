import subprocess
import sys
import os
import shutil
import argparse
from typing import List

def run_command(command: List[str], cwd: str = None) -> bool:
    """Run a shell command and return True if successful."""
    try:
        print(f"Executing: {' '.join(command)}")
        result = subprocess.run(command, cwd=cwd, check=False)
        if result.returncode != 0:
            print(f"Error: Command failed with exit code {result.returncode}")
            return False
        return True
    except FileNotFoundError:
        print(f"Error: Command not found: {command[0]}")
        return False
    except Exception as e:
        print(f"Error executing command: {e}")
        return False

def check_dependencies():
    """Check if required tools are installed."""
    required_tools = ["uv", "git", "gcloud"]
    missing = []
    for tool in required_tools:
        if shutil.which(tool) is None:
            missing.append(tool)
    
    if missing:
        print(f"Missing required tools: {', '.join(missing)}")
        print("Please install them and try again.")
        sys.exit(1)

def run_tests() -> bool:
    """Run local tests and linting."""
    print("\n--- Running Pre-deployment Checks ---")
    
    # Linting
    if not run_command(["uv", "run", "ruff", "check", "mcp_core", "frontend", "tests"]):
        return False
        
    # Type Checking
    if not run_command(["uv", "run", "mypy", "mcp_core", "--ignore-missing-imports"]):
        return False
        
    # Testing
    if not run_command(["uv", "run", "pytest", "tests"]):
        return False
        
    print("--- All Checks Passed ---")
    return True

def deploy_gcp(project_id: str, service_name: str, region: str):
    """Deploy backend to Google Cloud Run."""
    print(f"\n--- Deploying to GCP ({project_id}/{service_name}) ---")
    
    # Build and Submit
    # This assumes a Dockerfile is present or using buildpacks
    build_cmd = [
        "gcloud", "builds", "submit", 
        "--tag", f"gcr.io/{project_id}/{service_name}",
        "--project", project_id
    ]
    if not run_command(build_cmd):
        return False
        
    # Deploy
    deploy_cmd = [
        "gcloud", "run", "deploy", service_name,
        "--image", f"gcr.io/{project_id}/{service_name}",
        "--platform", "managed",
        "--region", region,
        "--project", project_id,
        "--allow-unauthenticated"
    ]
    if not run_command(deploy_cmd):
        return False
        
    print("--- GCP Deployment Complete ---")
    return True

def deploy_frontend(repo_url: str):
    """Deploy frontend to a separate GitHub repository."""
    print(f"\n--- Deploying Frontend to GitHub ({repo_url}) ---")
    
    # Check if frontend directory exists
    if not os.path.isdir("frontend"):
        print("Error: 'frontend' directory not found.")
        return False

    # Create a temporary directory for the frontend repo
    temp_dir = "frontend_deploy_temp"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    try:
        # Clone the repo (shallow clone)
        if not run_command(["git", "clone", "--depth", "1", repo_url, temp_dir]):
            # If clone fails (e.g., empty repo), verify and initialize might be needed, 
            # but for now we assume the repo exists as per instructions.
            print("Failed to clone repository. Please ensure it exists.")
            return False

        # Remove everything in the temp repo except .git
        for item in os.listdir(temp_dir):
            if item == ".git":
                continue
            item_path = os.path.join(temp_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)

        # Copy frontend contents to temp dir
        # We copy content of 'frontend' folder to root of repo
        for item in os.listdir("frontend"):
            s = os.path.join("frontend", item)
            d = os.path.join(temp_dir, item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
        
        # Git commit and push
        cwd = os.getcwd()
        os.chdir(temp_dir)
        
        run_command(["git", "add", "."])
        
        # Check for changes
        status_res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if not status_res.stdout.strip():
            print("No changes to deploy.")
        else:
            run_command(["git", "commit", "-m", "Deploy frontend"])
            run_command(["git", "push"])
            
        os.chdir(cwd)
        
    except Exception as e:
        print(f"Error deploying frontend: {e}")
        return False
    finally:
        if os.path.exists(temp_dir):
            # Cleanup might fail on Windows if git processes are lingering, but we try
            try:
                shutil.rmtree(temp_dir)
            except:
                print(f"Warning: Could not remove temp dir {temp_dir}")

    print("--- Frontend Deployment Complete ---")
    return True

def main():
    parser = argparse.ArgumentParser(description="Automated Deployment Script")
    parser.add_argument("--project-id", help="GCP Project ID", required=False)
    parser.add_argument("--repo-url", help="Frontend GitHub Repo URL", required=False)
    parser.add_argument("--skip-tests", action="store_true", help="Skip pre-flight tests")
    parser.add_argument("--dry-run", action="store_true", help="Simulate deployment")

    args = parser.parse_args()

    # 1. Pre-flight Checks
    check_dependencies()
    
    if not args.skip_tests:
        if not run_tests():
            print("Tests failed. Aborting deployment.")
            sys.exit(1)

    # 2. Deploy Logic
    if args.dry_run:
        print("Dry run enabled. Skipping actual deployment.")
        return

    # Validations for deployment
    if not args.project_id or not args.repo_url:
        print("Error: --project-id and --repo-url are required for deployment.")
        print("Usage: python deploy_manager.py --project-id my-project --repo-url https://github.com/user/repo")
        sys.exit(1)

    # Deploy Backend
    if not deploy_gcp(args.project_id, "function-store-mcp", "asia-northeast1"):
        print("Backend deployment failed.")
        sys.exit(1)

    # Deploy Frontend
    if not deploy_frontend(args.repo_url):
        print("Frontend deployment failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
