import pytest
import time
import random
import gc
from pathlib import Path
import solo_mcp.config
from solo_mcp.database import init_db

# Use session-wide counter to ensure unique paths even on fast CPU
_counter = 0

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Ensure the test data directory exists."""
    TEST_DATA_DIR = Path("data/tests")
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    yield

@pytest.fixture(scope="function", autouse=True)
def setup_db_isolation(monkeypatch):
    """
    For EACH test function, we provide a unique, fresh DuckDB file.
    """
    global _counter
    _counter += 1
    
    TEST_DATA_DIR = Path("data/tests")
    ts = int(time.time() * 1000)
    unique_id = f"{ts}_{_counter}_{random.randint(0, 999)}"
    test_db_path = TEST_DATA_DIR / f"test_{unique_id}.duckdb"
    
    # 1. Patch the global config source of truth
    # All modules use solo_mcp.database.get_db_connection() which now looks up solo_mcp.config.DB_PATH
    monkeypatch.setattr(solo_mcp.config, "DB_PATH", test_db_path)
    
    # 2. Force initialization of THIS fresh DB
    init_db()
    
    yield
    
    # 3. Cleanup
    gc.collect()
