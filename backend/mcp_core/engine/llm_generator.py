import json
import logging
from typing import Optional, Tuple

from google import genai
from google.genai import types
from mcp_core.core import config

logger = logging.getLogger(__name__)


class LLMDescriptionGenerator:
    """
    Generates function descriptions using Google's GenAI (Gemma/Gemini).
    """

    @classmethod
    def generate(cls, name: str, code: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Generates English and Japanese descriptions for the given code.
        Returns: (description_en, description_jp)
        """
        if not config.GOOGLE_API_KEY:
            logger.warning("Google API Key not set. Skipping auto-description.")
            return None, None

        try:
            client = genai.Client(api_key=config.GOOGLE_API_KEY)

            prompt = f"""
You are an expert Python developer. Analyze the following function and provide a concise summary in both English and Japanese.

Function Name: {name}
Code:
```python
{code[:2000]}
```

Output the result in strict JSON format with keys 'en' and 'jp'.
Example:
{{
  "en": "Calculates the Fibonacci sequence up to n terms.",
  "jp": "n項までのフィボナッチ数列を計算します。"
}}
            """

            response = client.models.generate_content(
                model=config.DESCRIPTION_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )

            if response.text:
                data = json.loads(response.text)
                return data.get("en"), data.get("jp")

            return None, None

        except Exception as e:
            logger.error(f"LLM Generation Error: {e}")
            return None, None
