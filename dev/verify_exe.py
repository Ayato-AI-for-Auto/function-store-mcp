import subprocess
import json
import os
import sys
import time

EXE_PATH = os.path.join("dist", "function_store_server.exe")

def test_exe():
    if not os.path.exists(EXE_PATH):
        print(f"Error: {EXE_PATH} not found. Build it first.")
        return

    print(f"Testing {EXE_PATH}...")
    
    # Start the EXE process with pipes
    proc = subprocess.Popen(
        [EXE_PATH],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0 # Unbuffered
    )

    # MCP Initialization Request (JSON-RPC)
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "TestClient", "version": "1.0"}
        }
    }
    
    try:
        # Send Request
        print("Sending Initialize Request...")
        json_line = json.dumps(init_request) + "\n"
        proc.stdin.write(json_line)
        proc.stdin.flush()
        
        # Read Response
        print("Waiting for response...")
        
        start_time = time.time()
        while time.time() - start_time < 10: # 10s timeout
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    print("Process exited prematurely.")
                    break
                continue
            
            print(f"Received: {line.strip()}")
            try:
                data = json.loads(line)
                if data.get("id") == 1:
                    print("✅ SUCCESS: Received initialize response!")
                    proc.terminate()
                    return
            except json.JSONDecodeError:
                pass # Log line

        # Check stderr if we failed/timed out
        err = proc.stderr.read()
        if err:
            print(f"Stderr: {err}")
            
        print("❌ FAILED: No valid JSON-RPC response received (Timeout).")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        if proc.poll() is None:
            proc.terminate()

if __name__ == "__main__":
    test_exe()