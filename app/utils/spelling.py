"""Spelling correction and text normalization utilities for Chip."""

from __future__ import annotations

from typing import Optional
import re


def normalize_text(text: str) -> str:
    """Normalize text by removing extra whitespace and fixing common issues."""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Fix common spacing issues around punctuation
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    text = re.sub(r'([.,!?;:])\s*([.,!?;:])', r'\1 \2', text)
    
    return text


def fix_common_typos(text: str) -> str:
    """Fix common typos and misspellings in user messages."""
    if not text:
        return ""
    
    # Common tech community typos
    corrections = {
        # Common word typos
        r'\bchallege\b': 'challenge',
        r'\bchalenges\b': 'challenges',
        r'\bchallange\b': 'challenge',
        r'\bchallanges\b': 'challenges',
        r'\bchalleng\b': 'challenge',
        r'\bchallengs\b': 'challenges',
        r'\bintership\b': 'internship',
        r'\binterships\b': 'internships',
        r'\binternship\b': 'internship',  # Common misspelling
        r'\binternships\b': 'internships',
        r'\boppurtunity\b': 'opportunity',
        r'\boppurtunities\b': 'opportunities',
        r'\bcomunity\b': 'community',
        r'\btechincal\b': 'technical',
        r'\btechincally\b': 'technically',
        r'\bsubmited\b': 'submitted',
        r'\bsubmition\b': 'submission',
        r'\bsubmitions\b': 'submissions',
        r'\bcompleated\b': 'completed',
        r'\bcompleate\b': 'complete',
        r'\boportunity\b': 'opportunity',
        r'\boportunities\b': 'opportunities',
        # Common abbreviations that might be misspelled
        r'\btech\s+comunity\b': 'tech community',
        r'\balabama\s+tech\s+comunity\b': 'alabama tech community',
    }
    
    corrected = text
    for pattern, replacement in corrections.items():
        corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
    
    return corrected


def correct_spelling(text: str, aggressive: bool = False) -> str:
    """Apply spelling corrections to text.
    
    Args:
        text: Input text to correct
        aggressive: If True, apply more aggressive corrections (may change intended words)
    
    Returns:
        Corrected text
    """
    if not text:
        return ""
    
    # First normalize the text
    normalized = normalize_text(text)
    
    # Apply common typo fixes
    corrected = fix_common_typos(normalized)
    
    if aggressive:
        # Additional aggressive corrections (use with caution)
        # These might change words that are intentionally misspelled
        aggressive_corrections = {
            r'\bwht\b': 'what',
            r'\bwat\b': 'what',
            r'\bwher\b': 'where',
            r'\bwen\b': 'when',
            r'\bhow\s+do\s+i\b': 'how do I',
            r'\bhow\s+can\s+i\b': 'how can I',
        }
        for pattern, replacement in aggressive_corrections.items():
            corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
    
    return corrected


def extract_clean_message(text: Optional[str]) -> str:
    """Extract and clean message text, handling None and empty strings."""
    if not text:
        return ""
    
    if not isinstance(text, str):
        text = str(text)
    
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
    # Normalize and correct
    cleaned = correct_spelling(text.strip())
    
    return cleaned

