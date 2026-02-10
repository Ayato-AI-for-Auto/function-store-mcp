# Core logic implementation for Function Store, free from any MCP or FastAPI decorators.
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional

from solo_mcp.database import get_db_connection
from solo_mcp.embedding import embedding_service
from solo_mcp.quality_gate import QualityGate
from solo_mcp.sanitizer import DataSanitizer
from solo_mcp.workers import background_verifier

logger = logging.getLogger(__name__)

def do_save_impl(asset_name: str, code: str, description: str = "", tags: List[str] = [], dependencies: List[str] = [], test_cases: List[Dict] = [], skip_test: bool = False, description_en: Optional[str] = None, description_jp: Optional[str] = None) -> str:
    """Core logic for saving a function."""
    sanitized = DataSanitizer.sanitize(asset_name, code, description, tags, description_en, description_jp)
    asset_name, code, description, tags = sanitized["name"], sanitized["code"], sanitized["description"], sanitized["tags"]
    description_en, description_jp = sanitized["description_en"], sanitized["description_jp"]

    conn = get_db_connection()
    try:
        gate = QualityGate()
        heal_report = gate.check_with_heal(asset_name, code, description_en or description, description_jp or description)
        
        if heal_report["status"] == "failed_code":
            code_rep = heal_report["code_report"]
            feedback = []
            if not code_rep["linter"]["passed"]:
                feedback.append(f"Linter errors: {', '.join(code_rep['linter']['errors'][:3])}")
            if not code_rep["reviewer"]["passed"]:
                feedback.append(f"AI Review: {code_rep['reviewer']['feedback']}")
            return "Quality Gate Failed (Code Issues). Improvements required: " + " | ".join(feedback)
            
        if heal_report["status"] == "failed_description":
            return f"Quality Gate Failed (Description Issues). {heal_report['failure_reason']} Feedback: {heal_report['description']['feedback']}"

        if heal_report["healed_desc_en"]:
            description_en = heal_report["healed_desc_en"]
        if heal_report["healed_desc_jp"]:
            description_jp = heal_report["healed_desc_jp"]

        logger.info(f"Quality Gate PASSED for '{asset_name}' (Score: {heal_report['score']}/100)")
        
        initial_status = "pending"
        error_log = ""
        if skip_test:
            initial_status = "unverified"
            error_log = "Verification SKIPPED"
        
        primary_desc = description_en if description_en else description_jp if description_jp else description
        text_to_embed = f"Function Name: {asset_name}\nDescription: {primary_desc}\nTags: {', '.join(tags)}\nDependencies: {', '.join(dependencies)}\nCode:\n{code[:1000]}"
        embedding = embedding_service.get_embedding(text_to_embed)
        vector_list = embedding.tolist()
        
        now = datetime.now().isoformat()
        metadata = {
            "dependencies": dependencies,
            "saved_at": now,
            "schema_version": "v2.0_duckdb",
            "quality_score": heal_report["score"],
            "quality_feedback": heal_report["description"]["feedback"],
            "heal_attempts": heal_report["heal_attempts"],
            "last_verified_at": now if skip_test else None,
            "verification_error": error_log if skip_test else None
        }
        
        existing = conn.execute("SELECT id, version, code, test_cases, description, description_en, description_jp FROM functions WHERE name = ?", (asset_name,)).fetchone()
        
        if existing:
            function_id, current_version = existing[0], int(existing[1]) if existing[1] else 1
            full_existing = conn.execute("SELECT metadata FROM functions WHERE id = ?", (function_id,)).fetchone()
            old_meta_json = full_existing[0] if full_existing else "{}"
            old_meta = json.loads(old_meta_json)
            old_deps = old_meta.get("dependencies", [])
            
            conn.execute('''
                INSERT INTO function_versions (id, function_id, version, code, dependencies, test_cases, description, description_en, description_jp, archived_at)
                VALUES (nextval('seq_version_id'), ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (function_id, current_version, existing[2], json.dumps(old_deps), existing[3], existing[4], existing[5], existing[6], now))
            
            new_version = current_version + 1
            conn.execute('''
                UPDATE functions SET
                    code=?, description=?, description_en=?, description_jp=?, tags=?, metadata=?, test_cases=?, status=?, updated_at=?, version=?, sync_status='pending'
                WHERE name=?
            ''', (code, description, description_en, description_jp, json.dumps(tags), json.dumps(metadata), json.dumps(test_cases), initial_status, now, str(new_version), asset_name))
        else:
            conn.execute('''
                INSERT INTO functions (name, code, description, description_en, description_jp, tags, metadata, test_cases, status, created_at, updated_at, version, org_id, sync_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (asset_name, code, description, description_en, description_jp, json.dumps(tags), json.dumps(metadata), json.dumps(test_cases), initial_status, now, now, '1', 'personal', 'pending'))
            function_id = conn.execute("SELECT id FROM functions WHERE name = ?", (asset_name,)).fetchone()[0]
            new_version = 1

        # Update embeddings: DELETE older ones first for the SAME function_id to avoid UNIQUE/PK constraint issues
        conn.execute("DELETE FROM embeddings WHERE function_id = ?", (function_id,))
        conn.execute("INSERT INTO embeddings (function_id, vector, model_name) VALUES (?, ?, ?)", (function_id, vector_list, embedding_service.model_name))
        conn.commit()
        
        if initial_status == "pending":
            background_verifier.queue_verification(asset_name, code, dependencies, test_cases)
            return f"SUCCESS: Function '{asset_name}' (v{new_version}) saved. Verification started in background."
        return f"SUCCESS: Function '{asset_name}' (v{new_version}) saved. Status: {initial_status}."
        
    except Exception as e:
        logger.error(f"Save Error: {e}", exc_info=True)
        raise e
    finally:
        conn.close()

def do_search_impl(query: str, limit: int = 5) -> List[Dict]:
    """Core logic for searching functions."""
    try:
        query_vector = embedding_service.get_embedding(query, is_query=True)
        q_vec_list = query_vector.tolist()
        conn = get_db_connection()
        try:
            # list_cosine_similarity expects (FLOAT[], FLOAT[])
            # We use an inner join to ensure we only compare against existing embeddings
            sql = """
                SELECT f.name, f.description, f.tags, f.metadata, f.status, f.test_cases, f.code,
                       f.description_en, f.description_jp, list_cosine_similarity(e.vector, ?::FLOAT[]) as score, e.model_name
                FROM embeddings e 
                JOIN functions f ON e.function_id = f.id 
                WHERE e.vector IS NOT NULL
                ORDER BY score DESC 
                LIMIT ?
            """
            results = conn.execute(sql, (q_vec_list, limit)).fetchall()
            
            output = []
            for r in results:
                meta = json.loads(r[3]) if r[3] else {}
                output.append({
                    "name": r[0],
                    "description": r[1],
                    "tags": json.loads(r[2]) if r[2] else [],
                    "dependencies": meta.get("dependencies", []),
                    "status": r[4],
                    "test_cases": json.loads(r[5]) if r[5] else [],
                    "score": r[9],
                    "code": r[6],
                    "description_en": r[7],
                    "description_jp": r[8]
                })
            return output
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

def do_get_impl(asset_name: str) -> str:
    """Core logic for retrieving a function."""
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT code FROM functions WHERE name = ?", (asset_name,)).fetchone()
        if row:
            now = datetime.now().isoformat()
            conn.execute("UPDATE functions SET call_count = call_count + 1, last_called_at = ? WHERE name = ?", (now, asset_name))
            conn.commit()
            return row[0]
        else:
            return f"Function '{asset_name}' not found."
    finally:
        conn.close()

def do_delete_impl(asset_name: str) -> str:
    """Core logic for deleting a function with manual cascaded cleanup."""
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT id FROM functions WHERE name = ?", (asset_name,)).fetchone()
        if row:
            fid = row[0]
            # Manual cascade for DuckDB - ensure order: dependencies first
            # 1. Embeddings refer to functions(id)
            conn.execute("DELETE FROM embeddings WHERE function_id = ?", (fid,))
            # 2. Versions refer to functions(id)
            conn.execute("DELETE FROM function_versions WHERE function_id = ?", (fid,))
            # 3. Finally functions
            conn.execute("DELETE FROM functions WHERE id = ?", (fid,))
            conn.commit()
            return f"SUCCESS: Function '{asset_name}' and its history deleted."
        return f"Error: Function '{asset_name}' not found."
    except Exception as e:
        logger.error(f"Delete Error: {e}")
        return f"Error: Failed to delete function '{asset_name}': {e}"
    finally:
        conn.close()

def do_get_history_impl(asset_name: str) -> List[Dict]:
    """Core logic for retrieving function history."""
    conn = get_db_connection()
    try:
        latest = conn.execute("SELECT version, description, updated_at FROM functions WHERE name = ?", (asset_name,)).fetchone()
        sql = """
            SELECT v.version, v.description, v.archived_at 
            FROM function_versions v 
            JOIN functions f ON v.id IS NOT NULL AND v.function_id = f.id 
            WHERE f.name = ? 
            ORDER BY v.version DESC
        """
        # Note: version_id check is a placeholder if we had more constraints
        archived = conn.execute(sql, (asset_name,)).fetchall()
        
        history = []
        if latest:
            history.append({
                "version": latest[0],
                "description": latest[1],
                "saved_at": latest[2],
                "is_current": True
            })
        for v in archived:
            history.append({
                "version": v[0],
                "description": v[1],
                "saved_at": v[2],
                "is_current": False
            })
        return history
    finally:
        conn.close()

def get_function_history(asset_name: str) -> List[Dict]:
    """Compatibility wrapper for tests."""
    return do_get_history_impl(asset_name)

def get_function_version(asset_name: str, version: int) -> Optional[Dict]:
    """Retrieve a specific version of a function."""
    conn = get_db_connection()
    try:
        sql = """
            SELECT v.version, v.code, v.description, v.archived_at
            FROM function_versions v
            JOIN functions f ON v.function_id = f.id
            WHERE f.name = ? AND v.version = ?
        """
        row = conn.execute(sql, (asset_name, version)).fetchone()
        if row:
            return {
                "version": row[0],
                "code": row[1],
                "description": row[2],
                "saved_at": row[3]
            }
        return None
    finally:
        conn.close()
