import json
import logging
from typing import Dict, List, Optional

from mcp_core.core.database import get_db_connection

logger = logging.getLogger(__name__)


class TriageEngine:
    """Identifies broken or low-quality functions and prepares diagnostic data."""

    def get_broken_functions(self, limit: int = 5) -> List[Dict]:
        """Returns a list of functions that have low quality scores or failed status."""
        conn = get_db_connection(read_only=False)
        try:
            # We look for functions that:
            # 1. Have a status of 'failed'
            # 2. Or have a quality_score < 70
            # 3. And are not 'deleted'
            # Extract quality_score from metadata JSON column
            query = "SELECT name, status, CAST(json_extract(metadata, '$.quality_score') AS INTEGER) as qs, description FROM functions WHERE qs < 70 AND status != 'deleted' ORDER BY qs ASC LIMIT ?"
            rows = conn.execute(query, (limit,)).fetchall()

            results = []
            for row in rows:
                results.append(
                    {
                        "name": row[0],
                        "status": row[1],
                        "quality_score": row[2],
                        "description": row[3],
                    }
                )
            return results
        finally:
            conn.close()

    def get_diagnostic_report(self, name: str) -> Optional[Dict]:
        """Fetches detailed error logs and metadata for a specific function with actionable advice."""
        conn = get_db_connection(read_only=False)
        try:
            # Extract quality_score from metadata JSON column
            query = "SELECT code, status, CAST(json_extract(metadata, '$.quality_score') AS INTEGER) as qs, metadata FROM functions WHERE name = ?"
            row = conn.execute(query, (name,)).fetchone()

            if not row:
                return None

            meta = json.loads(row[3]) if row[3] else {}
            status = row[1]
            qs = row[2]

            # Actionable Advice Logic
            advice = []
            if status == "broken":
                advice.append(
                    "CRITICAL: Syntax error detected. Use Cursor or your preferred AI to fix the code structure before deployment."
                )
            if qs < 50:
                advice.append(
                    "NOTE: Quality score is very low. Consider adding docstrings, type hints, and running a formatter."
                )
            if status == "failed":
                advice.append(
                    "WARNING: Unit tests failed. Review the test_results for specific failures."
                )
            if not advice:
                advice.append(
                    "Logic is stable. Minor refinements may improve the quality score further."
                )

            return {
                "name": name,
                "status": status,
                "quality_score": qs,
                "code": row[0],
                "errors": meta.get("errors", []),
                "verification_error": meta.get("verification_error", ""),
                "quality_feedback": meta.get("quality_feedback", ""),
                "security_report": meta.get("security", {}),
                "actionable_advice": advice,
                "dependencies": meta.get("dependencies", []),
                "internal_dependencies": meta.get("internal_dependencies", []),
            }
        finally:
            conn.close()


triage_engine = TriageEngine()
