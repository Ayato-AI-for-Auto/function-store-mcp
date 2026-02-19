import json
import logging
from typing import Dict, List, Optional

from mcp_core.core.database import get_db_connection

logger = logging.getLogger(__name__)


class TriageEngine:
    """Identifies broken or low-quality functions and prepares diagnostic data."""

    def get_broken_functions(self, limit: int = 5) -> List[Dict]:
        """Returns a list of functions that have low quality scores or failed status."""
        conn = get_db_connection(read_only=True)
        try:
            # We look for functions that:
            # 1. Have a status of 'failed'
            # 2. Or have a quality_score < 70 (Horiemon's threshold)
            # 3. And are not 'deleted'
            # Extract quality_score from metadata JSON column
            query = "SELECT name, version, status, CAST(json_extract(metadata, '$.quality_score') AS INTEGER) as qs, description FROM functions WHERE qs < 70 AND status != 'deleted' ORDER BY qs ASC LIMIT ?"
            rows = conn.execute(query, (limit,)).fetchall()

            results = []
            for row in rows:
                results.append(
                    {
                        "name": row[0],
                        "version": row[1],
                        "status": row[2],
                        "quality_score": row[3],
                        "description": row[4],
                    }
                )
            return results
        finally:
            conn.close()

    def get_diagnostic_report(self, name: str) -> Optional[Dict]:
        """Fetches detailed error logs and metadata for a specific function."""
        conn = get_db_connection(read_only=True)
        try:
            # Extract quality_score from metadata JSON column
            query = "SELECT code, status, CAST(json_extract(metadata, '$.quality_score') AS INTEGER) as qs, metadata FROM functions WHERE name = ?"
            row = conn.execute(query, (name,)).fetchone()

            if not row:
                return None

            meta = json.loads(row[3]) if row[3] else {}

            return {
                "name": name,
                "status": row[1],
                "quality_score": row[2],
                "code": row[0],
                "errors": meta.get("errors", []),
                "lint_results": meta.get("lint_results", ""),
                "test_results": meta.get("test_results", ""),
            }
        finally:
            conn.close()

    def generate_repair_advice(self, report: Dict) -> str:
        """Uses local LLM to generate a repair strategy based on the report."""
        from mcp_core.engine.llm_generator import LLMDescriptionGenerator

        llm = LLMDescriptionGenerator._get_llm()
        if not llm:
            return "Local LLM not available. Please inspect the logs manually."

        prompt = f"""
You are an expert Python developer and code quality auditor.
Analyze the following function and its error reports, then provide a concise "Repair Manual".

Function: {report["name"]}
Code:
```python
{report["code"]}
```

Diagnostics:
- Lint Errors: {report["lint_results"]}
- Test Failures: {report["test_results"]}

Provide:
1. A summary of what's broken.
2. A step-by-step fix strategy for an AI agent to follow.
3. If the fix is obvious (e.g., missing import), state it clearly.

Repair Manual:
"""
        try:
            response = llm.create_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful diagnostic assistant.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=512,
                temperature=0.1,
            )
            return response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"Triage LLM Error: {e}")
            return (
                f"Diagnostic analysis failed: {e}. Please use raw logs for debugging."
            )


triage_engine = TriageEngine()
