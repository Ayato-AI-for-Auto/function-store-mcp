import time

from mcp_core.engine.logic import (
    do_delete_impl,
    do_get_history_impl,
    do_save_impl,
    do_search_impl,
)


def test_full_save_search_delete_lifecycle():
    ts = int(time.time() * 1000)
    name = f"e2e_lifecycle_{ts}"
    code = f'def {name}():\n    """This is an E2E test function."""\n    return \'life cycle\''

    # 1. Save
    print(f"Step 1: Saving {name}")
    save_res = do_save_impl(
        asset_name=name, code=code, description="E2E Lifecycle Test"
    )
    assert "SUCCESS" in save_res

    # 2. Search
    print("Step 2: Searching (polling for background embedding)")
    found = False
    for _ in range(10):  # Max 5 seconds
        search_res = do_search_impl("E2E Lifecycle Test")
        if any(r["name"] == name for r in search_res):
            found = True
            break
        time.sleep(0.5)
    assert found, f"Function {name} not found in search results after save"

    # 3. History
    print("Step 3: Checking History")
    history = do_get_history_impl(name)
    print(f"History length: {len(history)}")
    if len(history) > 0:
        print(
            f"First history item: v{history[0]['version']} - {history[0]['description']}"
        )
    assert len(history) >= 1, (
        f"Expected at least 1 history item, got {len(history)}: {history}"
    )
    assert history[0]["version"] == 1

    # 4. Update (V2)
    print("Step 4: Updating to V2")
    code_v2 = f'def {name}():\n    """V2"""\n    return \'v2\''
    save_res_v2 = do_save_impl(
        asset_name=name, code=code_v2, description="E2E Lifecycle V2"
    )
    assert "SUCCESS" in save_res_v2

    history_v2 = do_get_history_impl(name)
    assert len(history_v2) == 2
    assert history_v2[0]["version"] == 2

    # 5. Delete
    print("Step 5: Deleting")
    del_res = do_delete_impl(name)
    assert "SUCCESS" in del_res

    # 6. Final Search (Should be gone)
    print("Step 6: Final availability check")
    final_search = do_search_impl(name)
    # Filter for exact match just in case of similar names
    exact_match = [r for r in final_search if r["name"] == name]
    assert len(exact_match) == 0
