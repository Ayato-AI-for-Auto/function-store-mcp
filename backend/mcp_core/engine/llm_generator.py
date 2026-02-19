import json
import logging
from typing import Optional, Tuple

from mcp_core.core import config

logger = logging.getLogger(__name__)


class LLMDescriptionGenerator:
    """
    Generates function descriptions using local LLM (Qwen via Llama.cpp).
    """

    _llm = None

    @classmethod
    def _get_llm(cls):
        if cls._llm is None:
            try:
                from huggingface_hub import hf_hub_download
                from llama_cpp import Llama

                logger.info(
                    f"LLM: Downloading/Checking model '{config.LLM_MODEL_ID}'..."
                )
                model_path = hf_hub_download(
                    repo_id=config.LLM_MODEL_ID,
                    filename=config.GGUF_FILENAME,
                    cache_dir=str(config.CACHE_DIR),
                )

                logger.info("LLM: Initializing Llama-cpp (CPU mode)...")
                cls._llm = Llama(
                    model_path=model_path, n_ctx=8192, n_gpu_layers=0, verbose=False
                )
                logger.info("LLM: Ready.")
            except ImportError:
                logger.error(
                    "LLM: 'llama-cpp-python' or 'huggingface_hub' not installed."
                )
                return None
            except Exception as e:
                logger.error(f"LLM: Failed to initialize local LLM: {e}")
                return None
        return cls._llm

    @classmethod
    def generate(cls, name: str, code: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Generates English and Japanese descriptions for the given code using local LLM.
        """
        llm = cls._get_llm()
        if not llm:
            return None, None

        try:
            prompt = f"""
Analyze the following function and provide a concise summary in both English and Japanese.
Output the result in strict JSON format with keys 'en' and 'jp'.

Function Name: {name}
Code:
```python
{code[:2000]}
```

JSON Output:
"""

            response = llm.create_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that outputs only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            text = response["choices"][0]["message"]["content"]
            if text:
                # Clean up potential markdown noise
                text = text.strip()
                if text.startswith("```json"):
                    text = text.split("```json")[1].split("```")[0].strip()
                elif text.startswith("```"):
                    text = text.split("```")[1].split("```")[0].strip()

                data = json.loads(text)
                return data.get("en"), data.get("jp")

            return None, None

        except Exception as e:
            logger.error(f"LLM Generation Error: {e}")
            return None, None
