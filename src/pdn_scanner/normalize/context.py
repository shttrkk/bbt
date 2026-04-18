from __future__ import annotations


def extract_context_window(text: str, start: int, end: int, window: int = 40) -> str:
    """Extract a small context window around a detected candidate."""
    left = max(0, start - window)
    right = min(len(text), end + window)
    return text[left:right]
