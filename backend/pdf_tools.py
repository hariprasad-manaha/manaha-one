from io import BytesIO
from typing import Optional

from pdfminer.high_level import extract_text

def pdf_bytes_to_text(data: bytes, max_chars: Optional[int] = None) -> str:
    """Extract text from a PDF byte string. Optionally truncate for safety."""
    try:
        text = extract_text(BytesIO(data)) or ""
        text = text.replace("\x00", " ").strip()
        if max_chars is not None and len(text) > max_chars:
            return text[:max_chars] + "\n...[truncated]"
        return text
    except Exception as e:
        return f"[PDF extraction error: {e}]"
