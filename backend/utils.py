import re
from typing import Any, Dict, List, Set, Union

# Heuristics for locating URLs in arbitrary JSON
URL_KEYS = {
    "url", "file_url", "download_url", "prescription_url", "link", "href", "document_url"
}

PDF_LIKE_PATTERNS = [
    re.compile(r"\.pdf(?:\?|$)", re.I),
]

PRESCRIPTION_HINTS = [
    re.compile(r"prescription", re.I),
    re.compile(r"rx", re.I),
    re.compile(r"consult", re.I),
    re.compile(r"medication", re.I),
    re.compile(r"treatment", re.I),
]

def _maybe_url(value: str) -> bool:
    if not isinstance(value, str):
        return False
    if value.startswith("http://") or value.startswith("https://"):
        return True
    return False

def _looks_like_prescription_url(value: str) -> bool:
    if any(p.search(value) for p in PDF_LIKE_PATTERNS):
        return True
    if any(p.search(value) for p in PRESCRIPTION_HINTS):
        return True
    return False

def extract_prescription_urls(obj: Union[Dict[str, Any], List[Any], Any]) -> List[str]:
    """Recursively walk a JSON-like structure and collect likely prescription/document URLs."""
    found: Set[str] = set()

    def walk(node: Union[Dict[str, Any], List[Any], Any]):
        if isinstance(node, dict):
            for k, v in node.items():
                lk = k.lower()
                if lk in URL_KEYS and isinstance(v, str) and _maybe_url(v) and _looks_like_prescription_url(v):
                    found.add(v)
                # If we see string fields with URLs even if key not in URL_KEYS
                if isinstance(v, str) and _maybe_url(v) and _looks_like_prescription_url(v):
                    found.add(v)
                elif isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        else:
            # Primitive other than string: ignore
            pass

    walk(obj)
    return sorted(found)
