import os
import pytest
import time
from solo_mcp.logic import do_save_impl as _do_save_impl, do_search_impl, do_delete_impl
from solo_mcp.database import get_db_connection
from solo_mcp.embedding import embedding_service

def test_full_registration_and_search_flow():
    """
    Integration test for the full flow:
    1. Register a new function.
    2. Verify it's in the database.
    3. Search for it and verify similarity.
    4. Cleanup.
    """
    ts = int(time.time())
    name = f"test_integration_add_{ts}"
    code = f"def {name}(a: int, b: int) -> int:\n    return a + b"
    description = "A simple function to add two numbers for integration testing."
    test_cases = [{"input": {"a": 1, "b": 2}, "expected": 3}]
    
    # Pre-cleanup to ensure fresh state
    do_delete_impl(name)
    
    # 1. Register
    result = _do_save_impl(
        asset_name=name,
        code=code,
        description=description,
        test_cases=test_cases,
        skip_test=True # Skip background verification for speed in unit test
    )
    
    assert "SUCCESS" in result
    
    # 2. Verify in DB
    conn = get_db_connection()
    row = conn.execute("SELECT id, description FROM functions WHERE name = ?", (name,)).fetchone()
    assert row is not None
    assert row[1] == description
    func_id = row[0]
    
    # Verify embedding created
    emb_row = conn.execute("SELECT vector FROM embeddings WHERE function_id = ?", (func_id,)).fetchone()
    assert emb_row is not None
    assert len(emb_row[0]) == 768
    
    # 3. Search
    search_results = do_search_impl("How to add two numbers?")
    
    assert len(search_results) > 0
    # Our function should be among the results
    found = any(r["name"] == name for r in search_results)
    assert found
    
    # 4. Cleanup
    del_res = do_delete_impl(name)
    assert "SUCCESS" in del_res
    
    # Final check: is it gone?
    row_final = conn.execute("SELECT id FROM functions WHERE name = ?", (name,)).fetchone()
    assert row_final is None
    conn.close()

def test_save_function_with_auto_heal():
    """
    Tests saving a function with a poor description to trigger auto-heal.
    Note: Requires GOOGLE_API_KEY to be set for actual LLM call.
    """
    if not os.environ.get("GOOGLE_API_KEY") and not embedding_service.api_key:
        pytest.skip("Skipping Auto-Heal integration test: No Google API Key")
        
    ts = int(time.time())
    name = f"test_poor_desc_{ts}"
    # Ensure name for pre-cleanup
    do_delete_impl(name)
    
    code = f"def test_poor_func_{ts}(x: int) -> int:\n    return x * 2"
    description = "bad desc" # Should trigger heal
    test_cases = [{"input": {"x": 5}, "expected": 10}]
    
    result = _do_save_impl(
        asset_name=name,
        code=code,
        description=description,
        test_cases=test_cases,
        skip_test=True
    )
    
    assert "SUCCESS" in result
    
    # Check if healed description is applied
    conn = get_db_connection()
    row = conn.execute("SELECT description_en FROM functions WHERE name = ?", (name,)).fetchone()
    assert row is not None
    assert row[0] != description # Should be replaced by high-quality EN desc
    
    do_delete_impl(name)
    conn.close()
