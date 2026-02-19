# Core logic implementation for Function Store, free from any MCP or FastAPI decorators.
import json
import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp_core.core import config
from mcp_core.core.database import get_db_connection
from mcp_core.engine.embedding import embedding_service
from mcp_core.engine.sanitizer import DataSanitizer

logger = logging.getLogger(__name__)


def do_save_impl(
    asset_name: str,
    code: str,
    description: str = "",
    tags: List[str] = [],
    dependencies: List[str] = [],
    test_cases: List[Dict] = [],
    skip_test: bool = False,
    description_en: Optional[str] = None,
    description_jp: Optional[str] = None,
) -> str:
    """Core logic for saving a function."""
    sanitized = DataSanitizer.sanitize(
        asset_name, code, description, tags, description_en, description_jp
    )
    asset_name, code, description, tags = (
        sanitized["name"],
        sanitized["code"],
        sanitized["description"],
        sanitized["tags"],
    )
    description_en, description_jp = (
        sanitized["description_en"],
        sanitized["description_jp"],
    )

    conn = get_db_connection()
    try:
        # --- MANDATORY LOCAL GATE (Free, Fast, Critical) ---
        # We always check these even if skip_test=True to prevent garbage/secrets from syncing.

        # 1. Syntax Check
        try:
            import ast

            ast.parse(code)
        except SyntaxError as se:
            return f"REJECTED: Syntax Error at line {se.lineno}: {se.msg}"

        # 2. Security & Secrets (Static Analysis)
        from mcp_core.core.security import ASTSecurityChecker, _contains_secrets

        is_safe, s_msg = ASTSecurityChecker.check(code)
        if not is_safe:
            return f"REJECTED: Security Block - {s_msg}"

        has_secret, secret_val = _contains_secrets(code)
        if has_secret:
            return "REJECTED: Secret detected in code. Please remove API keys or passwords."

        # 3. Quality Gate (Now Async/Background)
        # We NO LONGER BLOCK on Lint/Type errors here.
        # This allows "save first, score later".
        logger.info(
            f"Stage 1 Quality Gate passed for '{asset_name}'. Detailed checks queued."
        )

        initial_status = "pending"
        error_log = ""
        if skip_test:
            initial_status = "unverified"
            error_log = "Verification SKIPPED"

        # --- PHASE 2 REFORM: Fast Return ---
        # We handle metadata and DB insert first, then do embedding/sync in background.

        primary_desc = (
            description_en
            if description_en
            else description_jp
            if description_jp
            else description
        )
        now = datetime.now().isoformat()
        metadata = {
            "dependencies": dependencies,
            "saved_at": now,
            "schema_version": "v2.0_duckdb",
            "quality_score": 0 if not skip_test else 100,
            "quality_feedback": "Pending background verification",
            "heal_attempts": 0,
            "last_verified_at": now if skip_test else None,
            "verification_error": error_log if skip_test else None,
            "reliability_tier": "pending",  # high/medium/low/pending
        }

        existing = conn.execute(
            "SELECT id, version, code, test_cases, description, description_en, description_jp FROM functions WHERE name = ?",
            (asset_name,),
        ).fetchone()

        if existing:
            function_id, current_version = (
                existing[0],
                int(existing[1]) if existing[1] else 1,
            )
            full_existing = conn.execute(
                "SELECT metadata FROM functions WHERE id = ?", (function_id,)
            ).fetchone()
            old_meta_json = full_existing[0] if full_existing else "{}"
            old_meta = json.loads(old_meta_json)
            old_deps = old_meta.get("dependencies", [])

            conn.execute(
                """
                INSERT INTO function_versions (id, function_id, version, code, dependencies, test_cases, description, description_en, description_jp, archived_at)
                VALUES (nextval('seq_version_id'), ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    function_id,
                    current_version,
                    existing[2],
                    json.dumps(old_deps),
                    existing[3],
                    existing[4],
                    existing[5],
                    existing[6],
                    now,
                ),
            )

            new_version = current_version + 1
            conn.execute(
                """
                UPDATE functions SET
                    code=?, description=?, description_en=?, description_jp=?, tags=?, metadata=?, test_cases=?, status=?, updated_at=?, version=?
                WHERE name=?
            """,
                (
                    code,
                    description,
                    description_en,
                    description_jp,
                    json.dumps(tags),
                    json.dumps(metadata),
                    json.dumps(test_cases),
                    initial_status,
                    now,
                    str(new_version),
                    asset_name,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO functions (name, code, description, description_en, description_jp, tags, metadata, test_cases, status, created_at, updated_at, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    asset_name,
                    code,
                    description,
                    description_en,
                    description_jp,
                    json.dumps(tags),
                    json.dumps(metadata),
                    json.dumps(test_cases),
                    initial_status,
                    now,
                    now,
                    "1",
                ),
            )
            function_id = conn.execute(
                "SELECT id FROM functions WHERE name = ?", (asset_name,)
            ).fetchone()[0]
            new_version = 1

        conn.commit()

        # --- BACKGROUND TASKS (Embedding, Verify, Sync) ---
        def run_background_maintenance(
            f_name, f_code, p_desc, f_tags, f_deps, f_tests, skip_verify
        ):
            try:
                # Prepare background DB connection
                c2 = get_db_connection()
                try:
                    # 0. Auto-Description Generation (if missing)
                    if not p_desc or len(p_desc) < 10:
                        logger.info(
                            f"Description missing for '{f_name}'. Auto-generating via {config.DESCRIPTION_MODEL}..."
                        )
                        from mcp_core.engine.llm_generator import (
                            LLMDescriptionGenerator,
                        )

                        gen_en, gen_jp = LLMDescriptionGenerator.generate(
                            f_name, f_code
                        )

                        if gen_en and gen_jp:
                            p_desc = gen_en
                            c2.execute(
                                "UPDATE functions SET description_en = ?, description_jp = ?, description = ? WHERE name = ?",
                                (gen_en, gen_jp, gen_en, f_name),
                            )
                            c2.commit()

                    # 1. Dependency Analysis & Isolation
                    from mcp_core.engine.dependency_solver import DependencySolver

                    detected_deps = DependencySolver.extract_imports(f_code)
                    all_deps = list(set(f_deps + detected_deps))
                    logger.info(
                        f"Dependency Lock for '{f_name}': detected={detected_deps}, provided={f_deps}"
                    )

                    # 2. Embedding
                    logger.info(f"Generating embedding for '{f_name}' in background...")
                    txt = f"Function: {f_name}\nDesc: {p_desc}\nTags: {','.join(f_tags)}\nCode:\n{f_code[:500]}"
                    emb = embedding_service.get_embedding(txt)
                    v_list = emb.tolist()

                    # 3. Verification & Version Locking
                    verify_status = "verified"
                    verify_err = None
                    lock_data = []

                    if not skip_verify:
                        logger.info(
                            f"Running verification for '{f_name}' in background..."
                        )
                        from mcp_core.runtime.environment import env_manager
                        from mcp_core.runtime.runtime import _run_test_cases

                        passed, v_msg = _run_test_cases(f_code, f_tests, all_deps)
                        if not passed:
                            verify_status = "failed"
                            verify_err = v_msg
                        else:
                            python_exe, _ = env_manager.get_python_executable(all_deps)
                            if python_exe:
                                lock_data = env_manager.capture_freeze(python_exe)

                    # 4. Quality Scoring
                    quality_score = 0
                    reliability = "unknown"
                    try:
                        from mcp_core.engine.quality_gate import QualityGate

                        qg = QualityGate()
                        q_report = qg.check_score_only(f_name, f_code, p_desc, "")
                        quality_score = q_report.get("final_score", 0)
                        reliability = q_report.get("reliability", "low")
                    except Exception as qe:
                        logger.error(f"Quality Scoring Failed for '{f_name}': {qe}")

                    # Final Commit to DB
                    row = c2.execute(
                        "SELECT id, metadata FROM functions WHERE name = ?", (f_name,)
                    ).fetchone()
                    if row:
                        fid = row[0]
                        existing_meta = json.loads(row[1]) if row[1] else {}
                        existing_meta.update(
                            {
                                "verification_error": verify_err,
                                "quality_score": quality_score,
                                "reliability_tier": reliability,
                                "verified_dependencies": lock_data,
                                "detected_imports": detected_deps,
                            }
                        )

                        c2.execute(
                            "UPDATE functions SET status = ?, metadata = ? WHERE id = ?",
                            (verify_status, json.dumps(existing_meta), fid),
                        )
                        c2.execute(
                            "DELETE FROM embeddings WHERE function_id = ?", (fid,)
                        )
                        c2.execute(
                            "INSERT INTO embeddings (function_id, vector, model_name, dimension, encoded_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                            (fid, v_list, embedding_service.model_name, len(v_list)),
                        )
                        c2.commit()
                finally:
                    c2.close()
                logger.info(f"Background maintenance for '{f_name}' complete.")
            except Exception as ex:
                logger.error(f"Background Save Task Error for '{f_name}': {ex}")

        threading.Thread(
            target=run_background_maintenance,
            args=(
                asset_name,
                code,
                primary_desc,
                tags,
                dependencies,
                test_cases,
                skip_test,
            ),
            daemon=True,
        ).start()

        if not config.SYNC_ENABLED:  # We're likely in a test
            logger.info("Test Mode: Waiting for background tasks to settle...")
            time.sleep(2.0)

        return f"SUCCESS: Function '{asset_name}' (v{new_version}) saved. Background tasks (Embedding & Quality Scoring) initiated."

    except Exception as e:
        logger.error(f"Save Error: {e}", exc_info=True)
        raise e
    finally:
        conn.close()


def do_search_impl(query: str, limit: int = 20) -> List[Dict]:
    """Search for functions using semantic search."""
    import time

    # Simple retry logic for when search is called immediately after save
    # and background embedding might be in progress or DuckDB is temporarily busy.
    for attempt in range(3):
        try:
            results = _do_search_query(query, limit)
            if results:
                return results
            if attempt < 2:
                time.sleep(1.0)  # Wait for background tasks to progress
        except Exception as e:
            msg = str(e)
            if (
                "Binder Error" in msg
                or "Unique finder" in msg
                or "locked" in msg.lower()
            ):
                logger.warning(
                    f"Search: Temporary DuckDB contention, retrying {attempt + 1}/3..."
                )
                time.sleep(0.5)
                continue
            logger.error(f"Search error: {e}")
            return []

    return []


def _do_search_query(query: str, limit: int = 20) -> List[Dict]:
    """Internal semantic search implementation."""
    emb = embedding_service.get_embedding(query)
    vector_list = emb.tolist()

    conn = get_db_connection(read_only=True)
    try:
        # Cross-join with embeddings and calculate cosine similarity
        sql = """
            SELECT f.id, f.name, f.description, f.description_en, f.description_jp, f.tags, f.status, f.version,
                   list_cosine_similarity(e.vector, ?::FLOAT[]) as similarity
            FROM functions f
            JOIN embeddings e ON f.id = e.function_id
            WHERE f.status != 'deleted'
            ORDER BY similarity DESC
            LIMIT ?
        """
        rows = conn.execute(sql, (vector_list, limit)).fetchall()

        results = []
        for r in rows:
            results.append(
                {
                    "id": r[0],
                    "name": r[1],
                    "description": r[2],
                    "description_en": r[3],
                    "description_jp": r[4],
                    "tags": json.loads(r[5]) if r[5] else [],
                    "status": r[6],
                    "version": r[7],
                    "score": round(float(r[8]), 4),
                }
            )
        return results
    finally:
        conn.close()


def do_get_impl(asset_name: str) -> str:
    """Core logic for retrieving a function."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT code FROM functions WHERE name = ?", (asset_name,)
        ).fetchone()
        if row:
            now = datetime.now().isoformat()
            conn.execute(
                "UPDATE functions SET call_count = call_count + 1, last_called_at = ? WHERE name = ?",
                (now, asset_name),
            )
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
        row = conn.execute(
            "SELECT id FROM functions WHERE name = ?", (asset_name,)
        ).fetchone()
        if row:
            fid = row[0]
            conn.execute("DELETE FROM embeddings WHERE function_id = ?", (fid,))
            conn.execute("DELETE FROM function_versions WHERE function_id = ?", (fid,))
            conn.execute("DELETE FROM functions WHERE id = ?", (fid,))
            conn.commit()
            return f"SUCCESS: Function '{asset_name}' and its history deleted."
        return f"Error: Function '{asset_name}' not found."
    except Exception as e:
        logger.error(f"Delete Error: {e}")
        return f"Error: Failed to delete function '{asset_name}': {e}"
    finally:
        conn.close()


def do_get_details_impl(name: str) -> Dict:
    """Gets full metadata for a function."""
    conn = get_db_connection(read_only=True)
    try:
        sql = "SELECT id, name, status, version, description, description_en, description_jp, code, tags, call_count, last_called_at FROM functions WHERE name = ?"
        row = conn.execute(sql, [name]).fetchone()
        if not row:
            return {"error": f"Function '{name}' not found"}

        return {
            "id": row[0],
            "name": row[1],
            "status": row[2],
            "version": row[3],
            "description": row[4],
            "description_en": row[5],
            "description_jp": row[6],
            "code": row[7],
            "tags": json.loads(row[8]) if row[8] else [],
            "call_count": row[9],
            "last_called_at": row[10],
        }
    finally:
        conn.close()


def do_get_history_impl(asset_name: str) -> List[Dict]:
    """Core logic for retrieving function history."""
    conn = get_db_connection()
    try:
        latest = conn.execute(
            "SELECT version, description, updated_at FROM functions WHERE name = ?",
            (asset_name,),
        ).fetchone()
        sql = """
            SELECT v.version, v.description, v.archived_at 
            FROM function_versions v 
            JOIN functions f ON v.id IS NOT NULL AND v.function_id = f.id 
            WHERE f.name = ? 
            ORDER BY v.version DESC
        """
        archived = conn.execute(sql, (asset_name,)).fetchall()

        history = []
        if latest:
            history.append(
                {
                    "version": latest[0],
                    "description": latest[1],
                    "saved_at": latest[2],
                    "is_current": True,
                }
            )
        for v in archived:
            history.append(
                {
                    "version": v[0],
                    "description": v[1],
                    "saved_at": v[2],
                    "is_current": False,
                }
            )
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
                "saved_at": row[3],
            }
        return None
    finally:
        conn.close()


def do_list_impl(
    query: Optional[str] = None, tag: Optional[str] = None, limit: int = 100
) -> List[Dict]:
    """Core logic for listing functions with basic filtering."""
    conn = get_db_connection(read_only=True)
    try:
        sql = "SELECT id, name, status, version, description, description_en, description_jp, call_count, last_called_at, tags FROM functions"
        params = []
        where_clauses = []

        if tag:
            where_clauses.append("tags LIKE ?")
            params.append(f'%"{tag}"%')
        elif query:
            where_clauses.append("(name ILIKE ? OR description ILIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()

        output = []
        for r in rows:
            output.append(
                {
                    "id": r[0],
                    "name": r[1],
                    "status": r[2],
                    "version": r[3],
                    "description": r[4],
                    "description_en": r[5],
                    "description_jp": r[6],
                    "call_count": r[7],
                    "last_called_at": r[8],
                    "tags": json.loads(r[9]) if r[9] else [],
                }
            )
        return output
    finally:
        conn.close()


def get_stats_impl() -> Dict:
    """Core logic for getting database statistics."""
    conn = get_db_connection(read_only=True)
    try:
        total = conn.execute("SELECT count(*) FROM functions").fetchone()[0]
        active = conn.execute(
            "SELECT count(*) FROM functions WHERE status IN ('active', 'verified')"
        ).fetchone()[0]
        total_calls = (
            conn.execute("SELECT sum(call_count) FROM functions").fetchone()[0] or 0
        )
        recent = conn.execute(
            "SELECT name, updated_at FROM functions ORDER BY updated_at DESC LIMIT 5"
        ).fetchall()
        return {
            "total_functions": total,
            "active_functions": active,
            "total_calls": total_calls,
            "recent_activity": [{"name": r[0], "time": r[1]} for r in recent],
        }
    finally:
        conn.close()


def do_import_impl(function_data: Dict[str, Any]) -> str:
    """Imports a function from the public store into the local database."""
    name = function_data.get("name")
    code = function_data.get("code")
    description = function_data.get("description", "")
    tags = function_data.get("tags", [])
    metadata = function_data.get("metadata", {})
    test_cases = function_data.get("test_cases", [])
    if not name or not code:
        return "ERROR: Missing name or code in function data."
    dependencies = metadata.get("dependencies", [])
    return do_save_impl(
        asset_name=name,
        code=code,
        description=description,
        tags=tags,
        dependencies=dependencies,
        test_cases=test_cases,
        skip_test=True,
    )
