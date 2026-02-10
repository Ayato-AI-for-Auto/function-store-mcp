
import sys
import importlib
import os

def check_import(module_name, display_name=None):
    if display_name is None:
        display_name = module_name
    try:
        importlib.import_module(module_name)
        print(f"[OK] {display_name}")
        return True
    except ImportError as e:
        print(f"[FAIL] {display_name}: {e}")
        return False

def verify():
    print("=== Function Store MCP: System Verification ===
")
    
    # 1. Python Version
    print(f"Python Version: {sys.version.split()[0]}")
    if sys.version_info < (3, 10):
        print("[FAIL] Python 3.10+ required.")
    else:
        print("[OK] Python Version")

    # 2. Critical Libraries
    checks = [
        ("numpy", "NumPy"),
        ("duckdb", "DuckDB"),
        ("torch", "PyTorch"),
        ("sentence_transformers", "Sentence Transformers"),
        ("mcp", "FastMCP"),
        ("uv", "uv (Python Package)")
    ]
    
    print("
Checking Libraries...")
    all_ok = True
    for mod, name in checks:
        if not check_import(mod, name):
            all_ok = False
            
    # 3. CUDA Check
    print("
Checking GPU Acceleration...")
    try:
        import torch
        if torch.cuda.is_available():
            print(f"[OK] CUDA Available: {torch.cuda.get_device_name(0)}")
            print(f"     VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
        else:
            print("[WARN] CUDA Not Available. Running in CPU mode (Slower).")
            print("       If you have an NVIDIA GPU, check your drivers and PyTorch installation.")
    except:
        print("[FAIL] Could not check CUDA status.")

    # 4. Final Result
    print("
" + "="*40)
    if all_ok:
        print("✅ SYSTEM READY. You can start the server.")
    else:
        print("❌ ISSUES DETECTED. Please check the errors above.")
    print("="*40)

if __name__ == "__main__":
    verify()
