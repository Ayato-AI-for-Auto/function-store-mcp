import gc
import os

import numpy as np
import pytest
from mcp_core.core import config as mcp_config
from mcp_core.core.database import init_db
from mcp_core.engine.embedding import embedding_service


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
    monkeypatch.setattr(mcp_config, "DB_PATH", test_db_path)
    monkeypatch.setattr(mcp_config, "API_KEYS_DB_PATH", test_keys_path)
    # Disable features that are non-deterministic or slow in tests
    monkeypatch.setattr(mcp_config, "SYNC_ENABLED", False)
    # 2. Mock Embedding Service to avoid slow model loading/downloading
    monkeypatch.setattr(
        embedding_service,
        "get_embedding",
        lambda text, **kwargs: np.zeros(768, dtype=np.float32),
    )
    monkeypatch.setattr(
        embedding_service,
        "get_model_info",
        lambda: {"dimension": 768, "model_name": "mock"},
    )

    # 3. Bypass DBWriteLock in tests to avoid cross-process/thread deadlock in pytest
    from mcp_core.core import database

    monkeypatch.setattr(
        database,
        "DBWriteLock",
        type(
            "MockLock", (), {"__enter__": lambda s: s, "__exit__": lambda s, *a: None}
        ),
    )

    # 4. Force synchronous execution of background tasks in tests
    import threading

    def mock_start(self):
        self._target(*self._args, **self._kwargs)

    monkeypatch.setattr(threading.Thread, "start", mock_start)

    # 5. Force initialization of the fresh DB
    init_db()

    yield

    # 5. Cleanup
    gc.collect()
    try:
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)
        wal = test_db_path + ".wal"
        if os.path.exists(wal):
            os.unlink(wal)
    except OSError:
        pass
