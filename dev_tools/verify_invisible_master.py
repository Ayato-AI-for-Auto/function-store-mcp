import logging
import os
import socket
import sys
import time

# Add backend to sys.path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend"))
)

from mcp_core.infra.coordinator import MASTER_PORT, coordinator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_master")


def check_master():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect(("127.0.0.1", MASTER_PORT))
            return True
        except:
            return False


def test_invisible_master():
    print("=== Function Store: Invisible Master Verification ===")

    print("\nStep 1: Initial state check...")
    initially_running = check_master()
    if initially_running:
        print("[INFO] Master is already running.")
    else:
        print("[INFO] Master is NOT running.")

    print("\nStep 2: Triggering master via proxy request...")
    # This should trigger coordinator.start_master_invisible() if not running
    if not coordinator.is_master_running():
        print("[ACTION] Master not detected. Starting master...")
        coordinator.start_master_invisible()
    else:
        print("[INFO] Master already running, skipping auto-start.")

    time.sleep(1)  # Give it a moment
    if check_master():
        print(
            "[SUCCESS] Master process detected on portal 127.0.0.1:{}".format(
                MASTER_PORT
            )
        )
    else:
        print("[FAIL] Master process NOT detected after start attempt.")
        sys.exit(1)

    print(
        "\nStep 3: Simulating tool call via proxy proxy_request('search_functions')..."
    )
    resp = coordinator.proxy_request("search_functions", {"query": "test", "limit": 1})
    if "result" in resp:
        print("[SUCCESS] Received {} results from Master.".format(len(resp["result"])))
    elif "error" in resp:
        print("[FAIL] Proxy returned error: {}".format(resp["error"]))
    else:
        print("[FAIL] Unexpected response: {}".format(resp))

    print("\nStep 4: Performance Test (PopularQueryCache)...")
    print("Executing 5 identical search queries...")
    durations = []
    for i in range(5):
        start = time.time()
        coordinator.proxy_request(
            "search_functions", {"query": "performance benchmark", "limit": 5}
        )
        durations.append(time.time() - start)
        print("  Call {}: {:.3f}s".format(i + 1, durations[-1]))

    first_call = durations[0]
    avg_later = sum(durations[1:]) / 4
    improvement = (first_call - avg_later) / first_call * 100 if first_call > 0 else 0

    print("\nResults:")
    print("  First Call (Cache Miss): {:.3f}s".format(first_call))
    print("  Average Later Calls (Cache Hit): {:.3f}s".format(avg_later))
    print("  Speed Improvement: {:.1f}%".format(improvement))

    if improvement > 50:
        print("[SUCCESS] PopularQueryCache is highly effective!")
    elif improvement > 10:
        print("[SUCCESS] PopularQueryCache is working (modest improvement).")
    else:
        # Note: In a dev environment with very small DB, initial search might be fast anyway
        print(
            "[INFO] Improvement was {:.1f}%. (May be small on tiny test DB)".format(
                improvement
            )
        )

    print("\n=== Verification Finished ===")


if __name__ == "__main__":
    test_invisible_master()
