import os
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Model ID (TranslateGemma 4B)
MODEL_ID = "google/translategemma-4b-it"

class TranslationService:
    """Service for handling translations using TranslateGemma."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TranslationService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.pipe = None
        self.loaded = False
        self._initialized = True
        
        # Import HF_TOKEN from config
        try:
            from solo_mcp.config import HF_TOKEN
            self.hf_token = HF_TOKEN
        except ImportError:
            self.hf_token = os.getenv("HF_TOKEN")

    def load_model(self):
        """Lazy load the TranslateGemma model."""
        if self.loaded:
            return True
        
        if not self.hf_token:
            logger.warning("[TranslationService] No HF_TOKEN found. Translation disabled.")
            return False

        logger.info(f"[TranslationService] Loading {MODEL_ID}...")
        try:
            import torch
            from transformers import pipeline, BitsAndBytesConfig
            # Configure 4-bit quantization to save VRAM (requires bitsandbytes)
            try:
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                )
                
                self.pipe = pipeline(
                    "text-generation",
                    model=MODEL_ID,
                    token=self.hf_token,
                    model_kwargs={"quantization_config": bnb_config, "low_cpu_mem_usage": True},
                    device_map="cuda",
                )
                logger.info("[TranslationService] Model loaded successfully on GPU (4-bit).")
            except Exception as gpu_e:
                logger.warning(f"[TranslationService] GPU Load Failed: {gpu_e}. Falling back to CPU...")
                # Fallback to CPU without quantization
                self.pipe = pipeline(
                    "text-generation",
                    model=MODEL_ID,
                    token=self.hf_token,
                    model_kwargs={"low_cpu_mem_usage": True},
                    device_map="cpu",
                )
                logger.info("[TranslationService] Model loaded successfully on CPU.")
            
            self.loaded = True
            return True
        except Exception as e:
            logger.error(f"[TranslationService] CRITICAL: Model load failed: {e}")
            return False

    def detect_language(self, text: str) -> str:
        """Detect if text is Japanese or English based on character analysis."""
        if any('\u3040' <= c <= '\u309F' or '\u30A0' <= c <= '\u30FF' or '\u4E00' <= c <= '\u9FFF' for c in text):
            return "jp"
        return "en"

    def translate(self, text: str, target_lang: str = "ja") -> Optional[str]:
        """Translate text to the target language."""
        if not self.load_model():
            return None
        
        lang_name = "Japanese" if target_lang == "ja" else "English"
        # TranslateGemma prompt format
        prompt = f"Translate the following technical description to {lang_name}:\n\n{text}\n\nTranslation:"

        try:
            outputs = self.pipe(
                prompt,
                max_new_tokens=256,
                do_sample=False,
                num_beams=1,
            )
            result = outputs[0]["generated_text"]
            # Extract only the translated part after "Translation:"
            if "Translation:" in result:
                result = result.split("Translation:")[-1].strip()
            return result
        except Exception as e:
            logger.error(f"[TranslationService] Translation Error: {e}")
            return None

    def ensure_bilingual(self, description: str, description_en: Optional[str] = None, description_jp: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """Ensures that both English and Japanese descriptions are available if possible."""
        
        # Determine current status
        has_en = bool(description_en)
        has_jp = bool(description_jp)
        
        if has_en and has_jp:
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
        """Update the database with new descriptions and regenerate embedding if necessary."""
        from solo_mcp.database import get_db_connection
        from solo_mcp.embedding import embedding_service
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
