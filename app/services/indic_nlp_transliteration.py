"""
Indic NLP Library Transliteration Fallback for Indic Languages
"""
from typing import Optional
try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate
    INDIC_NLP_AVAILABLE = True
except ImportError:
    INDIC_NLP_AVAILABLE = False

def indic_nlp_transliterate(text: str, source_scheme: str, target_scheme: str) -> Optional[str]:
    if not INDIC_NLP_AVAILABLE:
        return None
    try:
        return transliterate(text, source_scheme, target_scheme)
    except Exception:
        return None
