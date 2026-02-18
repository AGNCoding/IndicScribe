"""
Unified Transliteration Service for Indic Languages
Primary: Google Cloud Transliteration
Fallback: Indic NLP Library
"""
from typing import Optional
from app.services.google_transliteration import GoogleTransliterationClient
from app.services.indic_nlp_transliteration import indic_nlp_transliterate

# Map UI/ISO codes to Google/IndicNLP codes as needed (only allowed languages)
LANG_CODE_MAP = {
    'devanagari': 'sa',  # Sanskrit (Devanagari)
    'kannada': 'kn',
    'hindi': 'hi',
    'telugu': 'te',
    'tamil': 'ta',
    'english': 'en',
}

class TransliterationService:
    def __init__(self):
        self.google_client = GoogleTransliterationClient()

    def transliterate(self, text: str, source: str, target: str) -> Optional[str]:
        src = LANG_CODE_MAP.get(source, source)
        tgt = LANG_CODE_MAP.get(target, target)
        # Try Google first
        result = self.google_client.transliterate(text, src, tgt)
        if result:
            return result
        # Fallback to Indic NLP
        return indic_nlp_transliterate(text, src, tgt)

def get_transliteration_service():
    return TransliterationService()
