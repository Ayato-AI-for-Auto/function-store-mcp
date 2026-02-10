import os
import sys
import json
import torch
import time
import traceback
from pathlib import Path
from transformers import pipeline, BitsAndBytesConfig

# Add the project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

# Configure HuggingFace cache to use project's data directory
HF_CACHE_DIR = PROJECT_ROOT / "data" / "models"
os.environ["HF_HOME"] = str(HF_CACHE_DIR)
os.environ["TRANSFORMERS_CACHE"] = str(HF_CACHE_DIR)

# Paths for Queue System
QUEUE_PATH = PROJECT_ROOT / "data" / "translation_queue.json"
RESULTS_PATH = PROJECT_ROOT / "data" / "translation_results.jsonl"

# Local Model ID (TranslateGemma 4B)
MODEL_ID = "google/translategemma-4b-it"

# Import HF_TOKEN from centralized config (loaded from UI settings)
try:
    from solo_mcp.config import HF_TOKEN
except ImportError:
    HF_TOKEN = os.getenv("HF_TOKEN")

class LocalTranslator:
    def __init__(self):
        self.pipe = None
        self.loaded = False

    def load_model(self):
        if self.loaded: return
        
        if not HF_TOKEN:
            print("[Translator] No HF_TOKEN found. Cannot load gated model.")
            return

        print(f"[Translator] Loading {MODEL_ID} (Local)...")
        try:
            print(f"[Translator] Attempting to load {MODEL_ID} on GPU (4-bit)...")
            # Configure 4-bit quantization to save VRAM
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )

            # Initialize translation pipeline on GPU
            self.pipe = pipeline(
                "text-generation", # TranslateGemma is decoder-only
                model=MODEL_ID,
                token=HF_TOKEN,
                model_kwargs={"quantization_config": bnb_config, "low_cpu_mem_usage": True},
                device_map="cuda",
            )
            self.loaded = True
            print("[Translator] Model loaded successfully on GPU.")
        except Exception as e:
            print(f"[Translator] GPU Load Failed: {e}")
            print("[Translator] Falling back to CPU (No Quantization)...")
            try:
                # Fallback to CPU without quantization
                self.pipe = pipeline(
                    "text-generation",
                    model=MODEL_ID,
                    token=HF_TOKEN,
                    model_kwargs={"low_cpu_mem_usage": True},
                    device_map="cpu",
                )
                self.loaded = True
                print("[Translator] Model loaded successfully on CPU.")
            except Exception as cpu_e:
                print(f"[Translator] CPU Load Failed: {cpu_e}")
                print(traceback.format_exc())

    def translate(self, text, target_lang="ja"):
        if not self.loaded or not self.pipe:
            return None
        
        # TranslateGemma prompt format
        # Based on: https://huggingface.co/google/translategemma-4b-it
        lang_name = "Japanese" if target_lang == "ja" else "English"
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
            print(f"[Translator] Translation Error: {e}")
            return None

def main():
    if not QUEUE_PATH.exists():
        print("[Translator] No queue file found.")
        return

    try:
        with open(QUEUE_PATH, "r", encoding="utf-8") as f:
            tasks = json.load(f)
    except Exception as e:
        print(f"[Translator] Queue Read Error: {e}")
        return

    if not tasks:
        print("[Translator] No tasks in queue.")
        return

    translator = LocalTranslator()
    translator.load_model()
    
    if not translator.loaded:
        print("[Translator] CRITICAL: Model load failed. Check HF_TOKEN and Hardware.")
        return

    print(f"[Translator] Processing {len(tasks)} tasks...")
    
    results = []
    for task in tasks:
        name = task.get("name")
        source_text = task.get("source")
        
        print(f"[Translator] Translating: {name}...")
        
        # Translate to JP if missing
        desc_jp = task.get("description_jp")
        if not desc_jp:
            desc_jp = translator.translate(source_text, target_lang="ja")
            
        # Translate to EN if missing
        desc_en = task.get("description_en")
        if not desc_en:
            desc_en = translator.translate(source_text, target_lang="en")

        if desc_jp or desc_en:
            results.append({
                "name": name,
                "description_en": desc_en or task.get("description_en"),
                "description_jp": desc_jp or task.get("description_jp")
            })

    if results:
        try:
            with open(RESULTS_PATH, "a", encoding="utf-8") as f:
                for res in results:
                    f.write(json.dumps(res, ensure_ascii=False) + "\n")
            print(f"[Translator] Successfully wrote {len(results)} results.")
        except Exception as e:
            print(f"[Translator] Result Write Error: {e}")

    # Remove queue after processing
    try:
        QUEUE_PATH.unlink()
        print("[Translator] Queue file cleared.")
    except: pass

if __name__ == "__main__":
    main()
