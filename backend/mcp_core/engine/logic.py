# Core logic implementation for Function Store, free from any MCP or FastAPI decorators.
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from mcp_core.core.database import DBWriteLock, get_db_connection
from mcp_core.engine.embedding import embedding_service
from mcp_core.engine.popular_query_cache import PopularQueryCache
from mcp_core.engine.quality_gate import QualityGate
from mcp_core.engine.router import router
from mcp_core.engine.sanitizer import DataSanitizer
from mcp_core.engine.worker import task_worker

logger = logging.getLogger(__name__)

quality_gate = QualityGate()
popular_cache = PopularQueryCache()


def do_save_impl(
    asset_name: str,
    code: str,
    description: str = "",
    tags: List[str] = [],
    dependencies: List[str] = [],
    test_cases: List[Dict] = [],
    skip_test: bool = False,
) -> str:
    """Core logic for saving a function."""
    if not description.strip():
        now_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        description = f"Draft automatically saved by AI on {now_date}"

    sanitized = DataSanitizer.sanitize(asset_name, code, description, tags)
    asset_name, code, description, tags = (
        sanitized["name"],
        sanitized["code"],
        sanitized["description"],
        sanitized["tags"],
    )

    with DBWriteLock():
        conn = get_db_connection()
        try:
            # --- MANDATORY LOCAL GATE (RELAXED) ---
            is_syntax_valid = True
            try:
                import ast

                ast.parse(code)
            except SyntaxError:
                is_syntax_valid = False

            from mcp_core.core.security import ASTSecurityChecker, _contains_secrets

            # Strict Security check ONLY if syntax is valid
            if is_syntax_valid:
                is_safe, s_msg = ASTSecurityChecker.check(code)
                if not is_safe:
                    return f"REJECTED: Security Block - {s_msg}"

            # Secret detection (text-based) is always mandatory
            has_secret, secret_val = _contains_secrets(code)
            if has_secret:
                return "REJECTED: Secret detected in code. Please remove API keys or passwords."

            initial_status = "pending" if is_syntax_valid else "broken"
            error_log = "" if is_syntax_valid else "Draft contains syntax errors."
            if skip_test:
                initial_status = "unverified"
                error_log = "Verification SKIPPED"

            now = datetime.now().isoformat()
            # Initial quality estimate
            initial_qs = 10 if not is_syntax_valid else (100 if skip_test else 0)

            metadata = {
                "dependencies": dependencies,
                "saved_at": now,
                "schema_version": "v2.0_duckdb",
                "quality_score": initial_qs,
                "quality_feedback": "Pending background verification"
                if is_syntax_valid
                else "Draft: Syntax Error",
                "last_verified_at": now if skip_test else None,
                "verification_error": error_log
                if skip_test or not is_syntax_valid
                else None,
                "reliability_tier": "low" if not is_syntax_valid else "pending",
                "verified_dependencies": [],
                "detected_imports": [],
                "internal_dependencies": [],
            }

            existing = conn.execute(
                "SELECT id, code, test_cases, description FROM functions WHERE name = ?",
                (asset_name,),
            ).fetchone()

            if existing:
                function_id, old_code, old_tests, old_desc = existing
                conn.execute(
                    """
                    UPDATE functions SET 
                        code=?, description=?, tags=?, metadata=?, test_cases=?, status=?, updated_at=? 
                    WHERE id = ?
                """,
                    (
                        code,
                        description,
                        json.dumps(tags),
                        json.dumps(metadata),
                        json.dumps(test_cases),
                        initial_status,
                        now,
                        function_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO functions (name, code, description, tags, metadata, test_cases, status, created_at, updated_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        asset_name,
                        code,
                        description,
                        json.dumps(tags),
                        json.dumps(metadata),
                        json.dumps(test_cases),
                        initial_status,
                        now,
                        now,
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    # --- BACKGROUND TASKS ---
    task_worker.add_task(
        run_background_maintenance,
        asset_name,
        code,
        description,
        tags,
        dependencies,
        test_cases,
        skip_test,
    )
    return f"SUCCESS: Asset '{asset_name}' saved in '{initial_status}' state. Background verification started."


def run_background_maintenance(
    f_name, f_code, f_desc, f_tags, f_deps, f_tests, skip_verify
):
    """Background task for dependency analysis, indexing, and quality scoring."""
    try:
        from mcp_core.engine.dependency_solver import DependencySolver

        detected_deps = DependencySolver.extract_imports(f_code)
        all_deps = list(set(f_deps + detected_deps))

        # Internal dependencies
        with DBWriteLock():
            conn = get_db_connection(read_only=False)
            try:
                all_func_names = {
                    r[0] for r in conn.execute("SELECT name FROM functions").fetchall()
                }
                internal_deps = DependencySolver.identify_internal_dependencies(
                    f_code, all_func_names
                )
            finally:
                conn.close()

        is_syntax_valid_bg = True
        try:
            import ast

            ast.parse(f_code)
        except SyntaxError:
            is_syntax_valid_bg = False

        verify_status = "verified" if is_syntax_valid_bg else "broken"
        verify_err = None if is_syntax_valid_bg else "Syntax Error detected in draft."
        lock_data = []

        if is_syntax_valid_bg and not skip_verify:
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

        # Generate embedding
        txt = f"Function: {f_name}\nDesc: {f_desc}\nTags: {','.join(f_tags)}\nCode:\n{f_code[:500]}"
        emb = embedding_service.get_embedding(txt)
        v_list = emb.tolist()

        # Quality Scoring
        quality_score = 0
        reliability = "low"
        try:
            q_report = quality_gate.check_score_only(f_name, f_code, f_desc, f_deps)
            quality_score = q_report.get("final_score", 0)
            reliability = q_report.get("reliability", "low")
        except Exception as qe:
            logger.error(f"Quality Scoring Failed for '{f_name}': {qe}")

        with DBWriteLock():
            c2 = get_db_connection()
            try:
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
                            "internal_dependencies": internal_deps,
                        }
                    )
                    c2.execute(
                        "UPDATE functions SET status = ?, metadata = ? WHERE id = ?",
                        (verify_status, json.dumps(existing_meta), fid),
                    )
                    c2.execute(
                        "DELETE FROM embeddings WHERE function_id = ? AND model_name = ?",
                        (fid, embedding_service.model_name),
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
        logger.error(
            f"Background Maintenance Error for '{f_name}': {ex}", exc_info=True
        )


def do_triage_list_impl(limit: int = 5) -> List[Dict]:
    """Core logic for listing broken functions."""
    from mcp_core.engine.triage import triage_engine

    return triage_engine.get_broken_functions(limit)


def do_search_impl(query: str, limit: int = 20) -> List[Dict]:
    """Search for functions using semantic search."""

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
    # 1. Check popular query cache
    query_embedding = popular_cache.get_embedding_cache(query)
    if query_embedding is None:
        # 2. Compute embedding if cache miss
        emb = embedding_service.get_embedding(query)
        query_embedding = emb.tolist()
        # 3. Cache if popular
        popular_cache.cache_embedding_if_popular(query, query_embedding)

    conn = get_db_connection(read_only=False)
    try:
        # 4. Search using the embedding
        sql = """
            SELECT f.id, f.name, f.description, f.tags, f.status,
                   list_cosine_similarity(e.vector, ?::FLOAT[]) as similarity,
                   COALESCE(CAST(json_extract(f.metadata, '$.quality_score') AS INTEGER), 50) as qs
            FROM functions f
            JOIN embeddings e ON f.id = e.function_id
            WHERE f.status != 'deleted' AND e.model_name = ?
            ORDER BY (similarity * 0.7 + (qs / 100.0) * 0.3) DESC
            LIMIT ?
        """
        rows = conn.execute(
            sql, (query_embedding, embedding_service.model_name, limit)
        ).fetchall()

        results = []
        for r in rows:
            results.append(
                {
                    "id": r[0],
                    "name": r[1],
                    "description": r[2],
                    "tags": json.loads(r[3]) if r[3] else [],
                    "status": r[4],
                    "similarity": round(float(r[5]), 4),
                    "quality_score": r[6],
                    "score": round(float(r[5]) * 0.7 + (r[6] / 100.0) * 0.3, 4),
                }
            )
        return results
    finally:
        conn.close()


def _resolve_bundle(name: str, visited: Set[str], codes: List[str]):
    """Recursively resolves internal dependencies and collects their code."""
    if name in visited:
        return
    visited.add(name)

    details = do_get_details_impl(name)
    if "error" in details:
        return

    code = details.get("code", "")
    internal_deps = details.get("metadata", {}).get("internal_dependencies", [])

    # Order: dependencies first (bottom-up)
    for dep in internal_deps:
        _resolve_bundle(dep, visited, codes)

    codes.append(f"# --- {name} ---\n{code}")


def do_get_impl(asset_name: str, integrate_dependencies: bool = False) -> str:
    """Core logic for retrieving a function, optionally with all its internal dependencies."""
    if integrate_dependencies:
        visited = set()
        codes = []
        _resolve_bundle(asset_name, visited, codes)
        if not codes:
            return f"Function '{asset_name}' not found."
        return "\n\n".join(codes)

    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT code FROM functions WHERE name = ?", (asset_name,)
        ).fetchone()
        if row:
            with DBWriteLock():
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
    with DBWriteLock():
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT id FROM functions WHERE name = ?", (asset_name,)
            ).fetchone()
            if row:
                fid = row[0]
                conn.execute("DELETE FROM embeddings WHERE function_id = ?", (fid,))
                conn.execute("DELETE FROM functions WHERE id = ?", (fid,))
                conn.commit()
                return f"SUCCESS: Function '{asset_name}' and its vector data deleted."
            return f"Error: Function '{asset_name}' not found."
        except Exception as e:
            logger.error(f"Delete Error: {e}")
            return f"Error: Failed to delete function '{asset_name}': {e}"
        finally:
            conn.close()


def do_get_details_impl(name: str) -> Dict:
    """Gets full metadata for a function."""
    conn = get_db_connection(read_only=False)
    try:
        # Schema version check: Ensure we handle optional columns
        sql = "SELECT id, name, status, description, tags, call_count, last_called_at, code, metadata FROM functions WHERE name = ?"
        row = conn.execute(sql, [name]).fetchone()
        if not row:
            return {"error": f"Function '{name}' not found"}

        return {
            "id": row[0],
            "name": row[1],
            "status": row[2],
            "description": row[3],
            "tags": json.loads(row[4]) if row[4] else [],
            "call_count": row[5],
            "last_called_at": row[6],
            "code": row[7],
            "metadata": json.loads(row[8]) if row[8] else {},
        }
    finally:
        conn.close()


def do_list_impl(
    query: Optional[str] = None, tag: Optional[str] = None, limit: int = 100
) -> List[Dict]:
    """Core logic for listing functions with basic filtering."""
    conn = get_db_connection(read_only=False)
    try:
        sql = "SELECT id, name, status, description, call_count, last_called_at, tags FROM functions"
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
                    "description": r[3],
                    "call_count": r[4],
                    "last_called_at": r[5],
                    "tags": json.loads(r[6]) if r[6] else [],
                }
            )
        return output
    finally:
        conn.close()


def get_stats_impl() -> Dict:
    """Core logic for getting database statistics."""
    conn = get_db_connection(read_only=False)
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


def do_inject_impl(function_names: List[str], target_dir: str) -> str:
    """
    Physical export of functions and their dependencies into local_pkg/.
    """
    from mcp_core.engine.package_generator import PackageGenerator

    visited = set()
    to_export = []

    def collect_recursive(name: str):
        if name in visited:
            return
        visited.add(name)

        details = do_get_details_impl(name)
        if "error" in details:
            logger.warning(f"Injection: Function '{name}' not found. Skipping.")
            return

        # Collect internal dependencies first
        internal_deps = details.get("metadata", {}).get("internal_dependencies", [])
        for dep in internal_deps:
            collect_recursive(dep)

        to_export.append({"name": name, "code": details.get("code", "")})

    for name in function_names:
        collect_recursive(name)

    if not to_export:
        return "No valid functions found to inject."

    return PackageGenerator.inject_package(target_dir, to_export)


def do_smart_get_impl(query: str, target_dir: str = "./") -> Dict:
    """
    Consolidated tool: Intent-based Search -> Selection -> Injection.
    """
    # 1. Search for candidates
    results = do_search_impl(query=query, limit=5)
    if not results:
        return {
            "status": "error",
            "message": f"No functions found for query: '{query}'",
        }

    # 2. Select the best match using IntelligenceRouter
    selected_name = router.evaluate_matching(query, results)
    if not selected_name:
        return {
            "status": "error",
            "message": "No suitable match found among candidates.",
            "candidates": [r["name"] for r in results],
        }

    # 3. Inject the selected function (and its dependencies)
    inject_result = do_inject_impl([selected_name], target_dir)

    # 4. Fetch metadata for reporting
    details = do_get_details_impl(selected_name)
    description = details.get("description", "No description available.")

    return {
        "status": "success",
        "selected_function": selected_name,
        "description": description,
        "injection_summary": inject_result,
        "target_dir": target_dir,
    }
