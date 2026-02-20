import logging
import threading

import numpy as np
from mcp_core.core.config import (
    CACHE_DIR,
    EMBEDDING_MODEL_ID,
    GEMINI_API_KEY,
    MODEL_TYPE,
)

# Suppress verbose third-party logging
logging.getLogger("fastembed").setLevel(logging.WARNING)
# google-genai logs can also be verbose
logging.getLogger("google.genai").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class GeminiEmbeddingService:
    """
    Cloud Embedding Service using Google Gemini (1536D).
    """

    def __init__(self):
        self.model_name = (
            "models/text-embedding-004"  # Latest recommended for embeddings
        )
        self._api_key = GEMINI_API_KEY
        self._client = None

    def _ensure_initialized(self):
        if self._client:
            return

        if not self._api_key:
            logger.error("GeminiEmbeddingService: API Key is missing. Check settings.")
            return

        try:
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
            logger.info("GeminiEmbeddingService: Initialized successfully.")
        except Exception as e:
            logger.error(f"GeminiEmbeddingService: Initialization Failed: {e}")

    def get_embedding(self, text: str, is_query: bool = False) -> np.ndarray:
        self._ensure_initialized()
        if not self._client:
            return np.zeros(1536, dtype=np.float32)

        try:
            # text-embedding-004 supports 1536D by default
            # We explicitly specify the model and text
            result = self._client.models.embed_content(
                model=self.model_name,
                contents=text,
                config={
                    "task_type": "RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT"
                },
            )
            # Result contains 'embeddings', which is a list of lists if batch,
            # or a single list if single content.
            # Using google-genai SDK
            vector = result.embeddings[0].values
            return np.array(vector, dtype=np.float32)

        except Exception as e:
            logger.error(f"GeminiEmbeddingService: Inference Failed - {e}")
            return np.zeros(1536, dtype=np.float32)

    def get_model_info(self) -> dict:
        return {
            "model_name": self.model_name,
            "dimension": 1536,
            "device": "cloud",
        }


class FastEmbeddingService:
    """
    Local Embedding Service using FastEmbed (ONNX).
    """

    _client_instance = None
    _init_lock = threading.Lock()

    def __init__(self):
        self.model_name = EMBEDDING_MODEL_ID
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of the FastEmbed client (Singleton)."""
        if FastEmbeddingService._client_instance is not None:
            self._initialized = True
            return

        with FastEmbeddingService._init_lock:
            if FastEmbeddingService._client_instance is not None:
                self._initialized = True
                return

            try:
                from fastembed import TextEmbedding

                logger.info(
                    f"FastEmbeddingService: Loading model '{self.model_name}'..."
                )
                FastEmbeddingService._client_instance = TextEmbedding(
                    model_name=self.model_name, cache_dir=str(CACHE_DIR)
                )
                self._initialized = True
                logger.info("FastEmbeddingService: Initialized successfully.")
            except ImportError:
                logger.error(
                    "FastEmbeddingService: 'fastembed' not installed. Run 'uv pip install fastembed'."
                )
            except Exception as e:
                logger.error(f"FastEmbeddingService: Initialization Failed: {e}")

    def get_embedding(self, text: str, is_query: bool = False) -> np.ndarray:
        """
        Get embedding vector using FastEmbed.
        """
        self._ensure_initialized()
        if not self._initialized or not FastEmbeddingService._client_instance:
            # Mock fallback if not initialized
            logger.warning(
                f"FastEmbeddingService not ready. Using zero vector for '{text[:20]}...'"
            )
            return np.zeros(768, dtype=np.float32)

        try:
            # FastEmbed returns a generator of numpy arrays
            embeddings = list(FastEmbeddingService._client_instance.embed([text]))
            if not embeddings:
                return np.zeros(768, dtype=np.float32)

            return np.array(embeddings[0], dtype=np.float32)

        except Exception as e:
            logger.error(f"FastEmbeddingService: Inference Failed - {e}")
            return np.zeros(768, dtype=np.float32)

    def get_model_info(self) -> dict:
        # Jina v2 base code is 768 dim
        dim = 768
        return {
            "model_name": self.model_name,
            "dimension": dim,
            "device": "cpu",  # Default for fastembed/onnx
        }


# Singleton Instance
if MODEL_TYPE == "gemini":
    embedding_service = GeminiEmbeddingService()
else:
    embedding_service = FastEmbeddingService()
