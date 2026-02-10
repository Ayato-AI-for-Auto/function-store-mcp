
import subprocess
import sys
import shutil

def has_nvidia_gpu():
    """
    Checks for NVIDIA GPU via nvidia-smi.
    """
    if shutil.which("nvidia-smi") is None:
        return False
    try:
        # Run nvidia-smi to confirm it actually works
        subprocess.check_call(["nvidia-smi"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

def install_torch():
    print("--- PyTorch Smart Installer ---")
    
    # Common packages (Latest versions for security fix)
    pkgs = ["torch>=2.6.0", "torchvision>=0.21.0", "torchaudio>=2.6.0"]
    
    if has_nvidia_gpu():
        print("[INFO] NVIDIA GPU detected. Installing CUDA 12.6 version...")
        print("       (This may take a while due to large download size ~2.5GB)")
        index_url = "https://download.pytorch.org/whl/cu126"
    else:
        print("[INFO] No NVIDIA GPU detected. Installing CPU version...")
        print("       (Lightweight installation)")
        index_url = "https://download.pytorch.org/whl/cpu"

    # Construct uv command
    cmd = ["uv", "pip", "install"] + pkgs + ["--index-url", index_url]
    
    try:
        subprocess.check_call(cmd)
        print("[SUCCESS] PyTorch installed successfully.")
    except subprocess.CalledProcessError:
        print("[ERROR] Failed to install PyTorch.")
        sys.exit(1)

if __name__ == "__main__":
    install_torch()
