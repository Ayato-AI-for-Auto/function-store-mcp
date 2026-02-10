
import os
import subprocess
import tempfile
import json
import logging
from typing import Tuple, List, Dict
from google import genai
from solo_mcp.config import GOOGLE_API_KEY, QUALITY_GATE_MODEL

logger = logging.getLogger(__name__)

class Linter:
    @staticmethod
    def check(code: str) -> Tuple[bool, List[str]]:
        """Checks code using Ruff."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            fname = f.name

        try:
            # Run Ruff
            result = subprocess.run(
                ["ruff", "check", fname, "--output-format=json"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                os.unlink(fname)
                return True, []
            
            errors = []
            try:
                data = json.loads(result.stdout)
                for item in data:
                    # Parse Ruff JSON output
                    code = item.get("code", "UNKNOWN")
                    message = item.get("message", "Unknown error")
                    row = item.get("location", {}).get("row", "?")
                    errors.append(f"Line {row} [{code}]: {message}")
            except json.JSONDecodeError:
                errors.append(f"Ruff Output: {result.stdout}")

            os.unlink(fname)
            return False, errors

        except Exception as e:
            if os.path.exists(fname):
                os.unlink(fname)
            return False, [f"Linter Exception: {str(e)}"]

class TypeChecker:
    @staticmethod
    def check(code: str) -> Tuple[bool, List[str]]:
        """Checks code using Mypy."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            fname = f.name

        try:
            # Run Mypy
            # --ignore-missing-imports: We don't have all libs in the env
            # --check-untyped-defs: Check inside functions even if not typed
            result = subprocess.run(
                ["mypy", fname, "--ignore-missing-imports", "--check-untyped-defs", "--no-color-output", "--no-error-summary"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                os.unlink(fname)
                return True, []

            errors = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            # Filter out the temporary filename from errors for cleaner output
            clean_errors = [e.replace(fname, "<code>") for e in errors]
            
            os.unlink(fname)
            return False, clean_errors

        except Exception as e:
            if os.path.exists(fname):
                os.unlink(fname)
            return False, [f"TypeChecker Exception: {str(e)}"]

class CodeReviewer:
    def __init__(self):
        self.api_key = GOOGLE_API_KEY
        self.model = QUALITY_GATE_MODEL
        self.client = None
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    def review(self, code: str) -> Tuple[bool, str]:
        """Reviews code using Gemini/Gemma."""
        if not self.client:
            return True, "LLM Review Skipped (No API Key)"

        prompt = f"""
        You are a strict Senior Python Engineer. Review the following code for a Function Store.
        
        CRITERIA:
        1. **Security**: No dangerous operations (subprocess, os.system, etc) unless absolutely necessary and safe.
        2. **Quality**: Clean, readable, Pythonic code.
        3. **Documentation**: Must have a docstring explaining what it does.
        4. **Typing**: Should use type hints.

        CODE:
        ```python
        {code}
        ```

        OUTPUT FORMAT:
        Start with "PASS" or "FAIL".
        Then provide a brief justification (1-2 sentences).
        If FAIL, explain what needs to be fixed.
        """

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            text = response.text.strip()
            
            if text.upper().startswith("PASS"):
                return True, text
            else:
                return False, text

        except Exception as e:
            logger.error(f"LLM Review Failed: {e}")
            return True, f"LLM Review Skipped (Error: {e})"

class DescriptionReviewer:
    """Reviews the semantic quality of function descriptions for search optimization."""
    def __init__(self):
        self.api_key = GOOGLE_API_KEY
        self.model = QUALITY_GATE_MODEL
        self.client = None
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    def review(self, name: str, code: str, desc_en: str, desc_jp: str) -> Tuple[int, str]:
        """
        Scores the description (0-100) based on how well it describes the code for search.
        Returns (score, feedback).
        """
        if not self.client:
            return 100, "Review Skipped (No API Key)"

        prompt = f"""
        You are an SEO and Search Discovery expert. Your task is to evaluate if the provided descriptions 
        accurately and comprehensively describe the Python function's purpose and usage for a Vector Search engine.

        FUNCTION NAME: {name}
        CODE:
        ```python
        {code}
        ```
        DESCRIPTION (EN): {desc_en}
        DESCRIPTION (JP): {desc_jp}

        CRITERIA:
        1. **Accuracy**: Does it match what the code actually does?
        2. **Discoverability**: Does it contain relevant keywords someone would use to find this tool?
        3. **Clarity**: Is it concise yet informative?

        OUTPUT FORMAT:
        Score: [0-100]
        Feedback: [Brief explanation of why and how to improve. Keep it under 2 sentences.]
        """

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            text = response.text.strip()
            
            # Simple parsing of "Score: X"
            score = 70 # Default
            for line in text.splitlines():
                if line.lower().startswith("score:"):
                    try:
                        score = int(line.split(":")[1].strip().split()[0])
                    except Exception:
                        pass
            
            return score, text

        except Exception as e:
            logger.error(f"Description Review Failed: {e}")
            return 70, f"Review Skipped (Error: {e})"

    def generate_description(self, name: str, code: str, feedback: str = "") -> Tuple[str, str]:
        """
        Generates optimized descriptions (EN, JP) based on code analysis.
        Uses previous feedback if provided for iterative improvement.
        Returns (desc_en, desc_jp).
        """
        if not self.client:
            return "No description generated (No API Key)", "説明文なし (APIキーなし)"

        feedback_section = ""
        if feedback:
            feedback_section = f"""
PREVIOUS FEEDBACK (use this to improve):
{feedback}
"""

        prompt = f"""
You are a technical writer creating PERFECT descriptions for a Function Store's Vector Search engine.
Your descriptions MUST be optimized for semantic search discovery.

FUNCTION NAME: {name}
CODE:
```python
{code}
```
{feedback_section}
TASK:
Generate TWO descriptions:
1. English (EN): A clear, keyword-rich description that someone would use to find this function.
2. Japanese (JP): A natural, accurate Japanese translation.

REQUIREMENTS:
- Include key technical terms and use cases.
- Be concise but comprehensive (1-2 sentences each).
- Match what the code actually does.

OUTPUT FORMAT (exactly):
EN: [Your English description]
JP: [Your Japanese description]
"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            text = response.text.strip()
            
            desc_en = ""
            desc_jp = ""
            for line in text.splitlines():
                if line.upper().startswith("EN:"):
                    desc_en = line.split(":", 1)[1].strip()
                elif line.upper().startswith("JP:"):
                    desc_jp = line.split(":", 1)[1].strip()
            
            return desc_en or "Generated description failed", desc_jp or "生成された説明文が失敗しました"

        except Exception as e:
            logger.error(f"Description Generation Failed: {e}")
            return f"Generation Error: {e}", f"生成エラー: {e}"

class QualityGate:
    def __init__(self):
        self.linter = Linter()
        self.typer = TypeChecker()
        self.reviewer = CodeReviewer()
        self.desc_reviewer = DescriptionReviewer()

    def check(self, name: str, code: str, desc_en: str, desc_jp: str) -> Dict:
        """Runs all checks (syntax, types, code quality, semantic quality) and returns a report."""
        report = {
            "status": "passed",
            "score": 100,
            "linter": {"passed": True, "errors": []},
            "typer": {"passed": True, "errors": []},
            "reviewer": {"passed": True, "feedback": ""},
            "description": {"score": 100, "feedback": ""}
        }

        score = 100
        # 1. Linter
        l_pass, l_errs = self.linter.check(code)
        report["linter"] = {"passed": l_pass, "errors": l_errs}
        if not l_pass: 
            report["status"] = "failed"
            score -= 30

        # 2. Type Checker
        t_pass, t_errs = self.typer.check(code)
        report["typer"] = {"passed": t_pass, "errors": t_errs}
        if not t_pass: 
            # Non-blocking for now, but penalize score
            score -= 10

        # 3. LLM Code Review
        r_pass, r_feedback = self.reviewer.review(code)
        report["reviewer"] = {"passed": r_pass, "feedback": r_feedback}
        if not r_pass: 
            report["status"] = "failed"
            score -= 40

        # 4. LLM Description Review (Semantic Quality)
        d_score, d_feedback = self.desc_reviewer.review(name, code, desc_en, desc_jp)
        report["description"] = {"score": d_score, "feedback": d_feedback}
        
        # Adjust global score based on semantic quality
        # Semantic quality is critical for discoverability
        if d_score < 60:
            report["status"] = "failed"
        
        # Final score calculation (Weighted average or min?)
        # Let's use the semantic score as a major factor
        report["score"] = min(score, d_score)

        return report

    def check_with_heal(self, name: str, code: str, desc_en: str, desc_jp: str, max_retries: int = 2) -> Dict:
        """
        Runs quality checks with auto-heal for descriptions.
        If description quality is low, attempts to generate better descriptions.
        Separates code quality from description quality issues.
        
        Returns report with:
        - status: 'passed', 'failed_code', 'failed_description'
        - healed_desc_en, healed_desc_jp: if auto-heal was applied
        - heal_attempts: number of heal iterations performed
        """
        # Step 1: Check Code Quality First
        code_report = {
            "status": "passed",
            "linter": {"passed": True, "errors": []},
            "typer": {"passed": True, "errors": []},
            "reviewer": {"passed": True, "feedback": ""}
        }
        
        l_pass, l_errs = self.linter.check(code)
        code_report["linter"] = {"passed": l_pass, "errors": l_errs}
        
        t_pass, t_errs = self.typer.check(code)
        code_report["typer"] = {"passed": t_pass, "errors": t_errs}
        
        r_pass, r_feedback = self.reviewer.review(code)
        code_report["reviewer"] = {"passed": r_pass, "feedback": r_feedback}
        
        # If code quality fails, return immediately with specific failure type
        if not l_pass or not r_pass:
            return {
                "status": "failed_code",
                "score": 0,
                "code_report": code_report,
                "description": {"score": 0, "feedback": "Code quality check failed. Fix code first."},
                "healed_desc_en": None,
                "healed_desc_jp": None,
                "heal_attempts": 0
            }
        
        # Step 2: Check Description Quality with Auto-Heal Loop
        current_desc_en = desc_en
        current_desc_jp = desc_jp
        last_feedback = ""
        
        for attempt in range(max_retries + 1):
            d_score, d_feedback = self.desc_reviewer.review(name, code, current_desc_en, current_desc_jp)
            
            if d_score >= 60:
                # Description quality is acceptable
                final_score = 100
                if not t_pass:
                    final_score -= 10  # Minor penalty for type issues
                final_score = min(final_score, d_score)
                
                return {
                    "status": "passed",
                    "score": final_score,
                    "code_report": code_report,
                    "description": {"score": d_score, "feedback": d_feedback},
                    "healed_desc_en": current_desc_en if attempt > 0 else None,
                    "healed_desc_jp": current_desc_jp if attempt > 0 else None,
                    "heal_attempts": attempt
                }
            
            # Description quality is low, attempt to heal
            if attempt < max_retries:
                logger.info(f"Auto-Heal Attempt {attempt + 1}/{max_retries} for '{name}' (Score: {d_score})")
                last_feedback = d_feedback
                current_desc_en, current_desc_jp = self.desc_reviewer.generate_description(name, code, last_feedback)
        
        # All retries exhausted, return failure with specific reason
        return {
            "status": "failed_description",
            "score": d_score,
            "code_report": code_report,
            "description": {"score": d_score, "feedback": d_feedback},
            "healed_desc_en": current_desc_en,
            "healed_desc_jp": current_desc_jp,
            "heal_attempts": max_retries,
            "failure_reason": f"Description quality remained below threshold after {max_retries} auto-heal attempts."
        }
