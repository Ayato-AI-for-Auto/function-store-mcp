import pytest
import time
from mcp_core.database import get_db_connection
from mcp_core.logic import do_save_impl as _do_save_impl
from mcp_core.workers import sync_agent, SyncAgent

@pytest.fixture(autouse=True)
def stop_global_sync_agent():
    # Stop the global auto-started agent to prevent race condition
    sync_agent.stop()
    yield

def test_sync_flow(monkeypatch):
    """Test the synchronization flow from pending to synced."""
    
    # Mock SyncEngine to work in test environment without Supabase
    def mock_push_function(self, func_data):
        conn = get_db_connection()
        conn.execute("UPDATE functions SET sync_status = 'synced' WHERE name = ?", (func_data["name"],))
        conn.commit()
        conn.close()

    def mock_is_connected(self):
        return True

    from mcp_core.sync_engine import SyncEngine
    monkeypatch.setattr(SyncEngine, "push_function", mock_push_function)
    monkeypatch.setattr(SyncEngine, "is_connected", mock_is_connected)
    # Note: DB_PATH is automatically handled by per-test isolation in conftest.py
    
    name = f"test_sync_fn_{int(time.time())}"
    code = "def test_sync_fn(): return 'synced'"
    description = "A function to test cloud sync."
    
    # 1. Save function (should be 'pending' initially)
    res_str = _do_save_impl(name, code, description, tags=["test"], skip_test=True)
    assert "SUCCESS" in res_str
    
    # 2. Verify initial sync_status is 'pending'
    conn = get_db_connection()
    res = conn.execute("SELECT sync_status FROM functions WHERE name = ?", (name,)).fetchone()
    conn.close()
    assert res is not None
    assert res[0] == 'pending'
    
    # 3. Start a designated SyncAgent for testing
    test_agent = SyncAgent(interval=1)
    test_agent.start()
    
    # 4. Wait for sync
    max_wait = 10
    synced = False
    
    for i in range(max_wait):
        time.sleep(1)
        conn = get_db_connection()
        res = conn.execute("SELECT sync_status FROM functions WHERE name = ?", (name,)).fetchone()
        conn.close()
        
        status = res[0] if res else "unknown"
        if status == 'synced':
            synced = True
            break
            
    test_agent.stop()
    assert synced, f"Expected status 'synced', but got '{status}'"
