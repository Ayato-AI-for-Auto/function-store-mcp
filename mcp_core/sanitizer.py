import re
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

class DataSanitizer:
    """
    Cleans and normalizes function data before registration.
    Focuses on:
    1. Converting full-width spaces to half-width.
    2. Stripping emojis from metadata and code (terminal stability).
    3. Trimming unnecessary whitespace.
    """
    
    # Unicode Emoji Regex Pattern
    # Matches various emoji ranges and miscellaneous symbols
    EMOJI_PATTERN = re.compile(
        "["
        "\U0001f600-\U0001f64f"  # emoticons
        "\U0001f300-\U0001f5ff"  # symbols & pictographs
        "\U0001f680-\U0001f6ff"  # transport & map symbols
        "\U0001f1e0-\U0001f1ff"  # flags
        "\U00002702-\U000027b0"
        "\U000024c2-\U0001f251"
        "\u2600-\u26ff"           # misc symbols
        "\u2700-\u27bf"           # dingbats
        "]+", flags=re.UNICODE
    )

    @classmethod
    def clean_text(cls, text: str) -> str:
        """Fixes spaces, removes emojis, and collapses redundant separators."""
        if not text:
            return ""
        
        # 1. Convert full-width space (\u3000) to half-width
        text = text.replace("\u3000", " ")
        
        # 2. Strip Emojis
        text = cls.EMOJI_PATTERN.sub("", text)
        
        # 3. Collapse multiple spaces created by stripping
        text = re.sub(r' +', ' ', text)
        
        # 4. Collapse multiple underscores (common in function names with emojis)
        text = re.sub(r'_+', '_', text)
        
        return text.strip()

    @classmethod
    def clean_code(cls, code: str) -> str:
        """
        Cleans source code of emojis to ensure terminal compatibility.
        Does NOT fix indentation (handled by Linter) but focuses on encoding safety.
        """
        if not code:
            return ""
        
        # Strip Emojis from the entire code block
        # (Safer than parsing AST for MVP, ensures terminal stability)
        cleaned_code = cls.EMOJI_PATTERN.sub("", code)
        
        # Convert full-width space to half-width even in code
        cleaned_code = cleaned_code.replace("\u3000", " ")
        
        return cleaned_code

    @classmethod
    def sanitize(cls, name: str, code: str, description: str, tags: List[str], desc_en: Optional[str] = None, desc_jp: Optional[str] = None) -> Dict[str, Any]:
        """Batch sanitize all registration fields."""
        # Clean each field, then filter out empty tags specifically
        cleaned_tags = []
        for t in tags:
            ct = cls.clean_text(t)
            if ct:
                cleaned_tags.append(ct)
                
        return {
            "name": cls.clean_text(name),
            "code": cls.clean_code(code),
            "description": cls.clean_text(description),
            "tags": cleaned_tags,
            "description_en": cls.clean_text(desc_en) if desc_en else None,
            "description_jp": cls.clean_text(desc_jp) if desc_jp else None
        }
