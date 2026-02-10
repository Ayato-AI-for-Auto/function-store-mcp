
import PyInstaller.__main__
import os
import shutil

def build():
    print("Building Function Store MCP exe...")
    
    # Clean previous builds
    if os.path.exists("dist"): shutil.rmtree("dist")
    if os.path.exists("build"): shutil.rmtree("build")

    # Entry point
    script = os.path.join("function_store_mcp", "server.py")
    
    # PyInstaller arguments
    args = [
        script,
        '--name=function_store_server',
        '--onefile',  # Single exe (slower start but easier distribution)
        '--clean',
        '--console',  # Keep console for logs (change to --noconsole for production hidden)
        
        # Hidden imports crucial for these libs
        '--hidden-import=sentence_transformers',
        '--hidden-import=duckdb',
        '--hidden-import=numpy',
        '--hidden-import=torch',
        '--hidden-import=scipy.special.cython_special', # Common scipy issue
        '--hidden-import=sklearn.utils._typedefs',      # Common sklearn issue
        
        # Data collections (Using collect_all might be needed in spec, but trying basics first)
        '--collect-all=sentence_transformers',
        '--collect-all=duckdb',
    ]
    
    PyInstaller.__main__.run(args)

if __name__ == "__main__":
    build()
