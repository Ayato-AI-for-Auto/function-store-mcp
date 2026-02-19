import logging
import threading

import numpy as np
from mcp_core.core.config import CACHE_DIR, EMBEDDING_MODEL_ID

# Suppress verbose third-party logging
logging.getLogger("fastembed").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


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
embedding_service = FastEmbeddingService()
