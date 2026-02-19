import threading
import time

from mcp_core.engine.logic import do_save_impl


def test_concurrent_save_resilience():
    """Verify that multiple simultaneous saves don't cause fatal DB corruption."""
    errors = []

    def worker(idx):
        try:
            name = f"concurrent_func_{idx}_{int(time.time() * 1000)}"
            res = do_save_impl(
                name, "def c(): pass", f"Concurrent {idx}", skip_test=True
            )
            if "SUCCESS" not in res:
                errors.append(f"Worker {idx} failed: {res}")
        except Exception as e:
            errors.append(f"Worker {idx} exception: {e}")

    threads = []
    for i in range(5):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # DuckDB handles concurrent connections fairly well, but let's check for errors
    # Note: If they all pass, it's a success.
    assert len(errors) == 0, f"Concurrent saves had errors: {errors}"
