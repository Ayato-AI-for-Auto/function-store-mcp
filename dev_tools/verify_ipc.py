import os
import sys
import time

# Add backend to path
sys.path.insert(0, os.path.join(os.getcwd(), "backend"))

from mcp_core.infra.ipc_manager import IPCManager


def mock_executor(tool, args):
    return f"Executed {tool} with {args}"


def test_ipc():
    print("--- IPC Verification Start ---")

    # Node 1: Should become Master
    mgr1 = IPCManager()
    role1, _ = mgr1.determine_role()
    print(f"Node 1 Role: {role1}")

    if role1 == "MASTER":
        mgr1.start_master_loop(mock_executor)
    else:
        print("FAILED: Node 1 should be MASTER")
        return

    time.sleep(1)  # Give master a second to start

    # Node 2: Should become Proxy
    mgr2 = IPCManager()
    role2, _ = mgr2.determine_role()
    print(f"Node 2 Role: {role2}")

    if role2 == "PROXY":
        resp = mgr2.proxy_call("test_tool", {"param": "val"})
        print(f"Proxy Call Response: {resp}")
    else:
        print("FAILED: Node 2 should be PROXY")

    # Cleanup
    mgr2.close()
    mgr1.close()
    print("--- IPC Verification Done ---")


if __name__ == "__main__":
    test_ipc()
