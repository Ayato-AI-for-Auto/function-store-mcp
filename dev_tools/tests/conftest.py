import gc
import os

import mcp_core.core.config
import pytest
from mcp_core.core.database import init_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Ensure basic test requirements."""
    yield


@pytest.fixture(scope="function", autouse=True)
def setup_db_isolation(monkeypatch, tmp_path):
    """
    For EACH test function, create a unique temporary DuckDB file.
    :memory: is per-connection in DuckDB, so multi-connection logic
    (like logic.py) requires a shared file path.
    """
    test_db_path = str(tmp_path / "test.duckdb")
    test_keys_path = str(tmp_path / "test_keys.duckdb")

    # 1. Patch the global config source of truth
    monkeypatch.setattr(mcp_core.core.config, "DB_PATH", test_db_path)
    monkeypatch.setattr(mcp_core.core.config, "API_KEYS_DB_PATH", test_keys_path)

    # 2. Force initialization of the fresh DB
    init_db()

    yield

    # 3. Cleanup
    gc.collect()
    try:
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)
        wal = test_db_path + ".wal"
        if os.path.exists(wal):
            os.unlink(wal)
    except OSError:
        pass
