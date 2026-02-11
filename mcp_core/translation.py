import logging
from typing import Optional, Tuple
from google import genai
from google.genai import types
from mcp_core import config

logger = logging.getLogger(__name__)

# Model ID for translation (High-quality Gemma 3)
MODEL_ID = "models/gemma-3-27b-it"

class TranslationService:
    """Service for handling translations using Google GenAI API."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TranslationService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.client = None
        self._initialized = True
        
        if config.GOOGLE_API_KEY:
            try:
                self.client = genai.Client(api_key=config.GOOGLE_API_KEY)
                logger.info(f"[TranslationService] Initialized with model '{MODEL_ID}'")
            except Exception as e:
                logger.error(f"[TranslationService] Client Init Failed: {e}")

    def is_available(self) -> bool:
        """Check if translation service is ready to use."""
        return self.client is not None and config.FS_ENABLE_TRANSLATION

    def detect_language(self, text: str) -> str:
        """Detect if text is Japanese or English based on character analysis."""
        if any('\u3040' <= c <= '\u309F' or '\u30A0' <= c <= '\u30FF' or '\u4E00' <= c <= '\u9FFF' for c in text):
            return "jp"
        return "en"

    def translate(self, text: str, target_lang: str = "ja") -> Optional[str]:
        """Translate text to the target language via API."""
        if not self.is_available():
            return None
        
        lang_name = "Japanese" if target_lang == "ja" else "English"
        prompt = f"Translate the following technical description to {lang_name}. Output ONLY the translated text.\n\n{text}"

        try:
            response = self.client.models.generate_content(
                model=MODEL_ID,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    top_p=0.95,
                    max_output_tokens=512,
                )
            )
            if response.text:
                return response.text.strip()
            logger.warning(f"[TranslationService] API Empty Response: {response}")
            return None
        except Exception as e:
            logger.error(f"[TranslationService] API Translation Error: {e}")
            print(f"DEBUG: Translation Error - {type(e).__name__}: {e}")
            return None

    def ensure_bilingual(self, description: str, description_en: Optional[str] = None, description_jp: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """Ensures that both English and Japanese descriptions are available if possible."""
        
        # Determine current status
        has_en = bool(description_en)
        has_jp = bool(description_jp)
        
        if has_en and has_jp:
            return description_en, description_jp
            
        # Check availability before trying
        if not self.is_available():
            # If not available, we can't do anything, just return what we have
            return description_en, description_jp

        # If both are missing, detect source language from primary description
        if not has_en and not has_jp:
            source_lang = self.detect_language(description)
            if source_lang == "jp":
                description_jp = description
                description_en = self.translate(description, target_lang="en")
            else:
                description_en = description
                description_jp = self.translate(description, target_lang="ja")
        elif not has_en and description_jp:
            # JP exists, translate to EN
            description_en = self.translate(description_jp, target_lang="en")
        elif not has_jp and description_en:
            # EN exists, translate to JP
            description_jp = self.translate(description_en, target_lang="ja")
            
        return description_en, description_jp

    def update_function_descriptions(self, name: str, desc_en: Optional[str], desc_jp: Optional[str]):
        """Update the database with new descriptions and regenerate embedding."""
        from mcp_core.database import get_db_connection
        from mcp_core.embedding import embedding_service
        import json
        
        conn = get_db_connection()
        try:
            # Update descriptions
            conn.execute(
                "UPDATE functions SET description_en = ?, description_jp = ?, sync_status = 'pending' WHERE name = ?",
                (desc_en, desc_jp, name)
            )
            
            # Fetch full data to regenerate embedding with English priority
            row = conn.execute("SELECT id, tags, metadata FROM functions WHERE name = ?", (name,)).fetchone()
            if row:
                fid, tags_json, meta_json = row
                tags = json.loads(tags_json) if tags_json else []
                # Regenerate Embedding
                primary_desc = desc_en if desc_en else desc_jp
                text_to_embed = f"Function Name: {name}\nDescription: {primary_desc}\nTags: {', '.join(tags)}\nCode:\n[Truncated]"
                
                embedding = embedding_service.get_embedding(text_to_embed)
                vector_list = embedding.tolist()
                
                conn.execute("DELETE FROM embeddings WHERE function_id = ?", (fid,))
                conn.execute("INSERT INTO embeddings (function_id, vector, model_name) VALUES (?, ?, ?)", (fid, vector_list, embedding_service.model_name))
            
            conn.commit()
            logger.info(f"[TranslationService] Background update/embedding OK for '{name}'")
        except Exception as e:
            logger.error(f"[TranslationService] Failed to update function after translation: {e}")
        finally:
            conn.close()

# Global instance
translation_service = TranslationService()
