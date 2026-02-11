import logging
import numpy as np
import hashlib
from google import genai
from google.genai import types
from mcp_core.config import MODEL_NAME, GOOGLE_API_KEY

logger = logging.getLogger(__name__)

class GeminiEmbeddingService:
    """
    Lightweight Embedding Service using Google Gemini API.
    Model: models/text-embedding-004 (768 dimensions)
    """
    def __init__(self):
        self.model_name = MODEL_NAME
        self.api_key = GOOGLE_API_KEY
        self.client = None
        self._initialized = False
        
        if not self.api_key:
            logger.warning("GeminiEmbeddingService: No API Key provided. Mock mode enabled.")
        else:
            try:
                self.client = genai.Client(api_key=self.api_key)
                self._initialized = True
                logger.info(f"GeminiEmbeddingService: Initialized with model '{self.model_name}'")
            except Exception as e:
                logger.error(f"GeminiEmbeddingService: Client Init Failed: {e}")

    def get_embedding(self, text: str, is_query: bool = False) -> np.ndarray:
        """
        Get embedding vector using Gemini API.
        """
        if not self.client:
             # Fallback/Mock for testing without key
             seed = int(hashlib.sha256(text.encode('utf-8')).hexdigest(), 16) % (2**32)
             rng = np.random.default_rng(seed)
             return rng.random(768, dtype=np.float32)

        try:
            # Gemini API call
            result = self.client.models.embed_content(
                model=self.model_name,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT"
                )
            )
            return np.array(result.embeddings[0].values, dtype=np.float32)

        except Exception as e:
            logger.error(f"GeminiEmbeddingService: API Call Failed - {e}")
            # Mock fallback to prevent crash, but log error
            return np.zeros(768, dtype=np.float32)
    
    def get_model_info(self) -> dict:
        return {
            "model_name": self.model_name,
            "dimension": 768,
            "device": "cloud-api"
        }

# Singleton Instance
embedding_service = GeminiEmbeddingService()
