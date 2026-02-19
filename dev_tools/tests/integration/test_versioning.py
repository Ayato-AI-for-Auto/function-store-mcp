import time

from mcp_core.engine.logic import do_get_history_impl, do_save_impl

# No local setup needed, handled by conftest.py


def test_versioning_flow():
    ts = int(time.time())
    name = f"version_test_{ts}"

    # 1. Save V1
    code_v1 = "def test(): return 'v1'"
    res = do_save_impl(
        asset_name=name,
        code=code_v1,
        description="Version 1",
        test_cases=[],
        skip_test=True,
    )
    assert "SUCCESS" in res

    # 2. Save V2
    code_v2 = "def test(): return 'v2'"
    res = do_save_impl(
        asset_name=name,
        code=code_v2,
        description="Version 2",
        test_cases=[],
        skip_test=True,
    )
    assert "SUCCESS" in res

    # 3. Check history
    history = do_get_history_impl(asset_name=name)
    assert len(history) >= 2
    assert history[0]["description"] == "Version 2"
    assert history[1]["description"] == "Version 1"
    assert history[0]["is_current"] is True
    assert history[1]["is_current"] is False
