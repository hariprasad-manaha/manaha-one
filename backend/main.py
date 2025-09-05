import os
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from utils import extract_prescription_urls
from pdf_tools import pdf_bytes_to_text
from gemini_client import init_gemini, summarize_patient_journey
from auth import eka_auth_header
from fastapi import Query

# --- Load .env from backend folder explicitly ---
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

EKA_BASE_URL = os.environ.get("EKA_BASE_URL", "https://api.eka.care")

app = FastAPI(title="Patient Journey Summarizer API", version="0.2.0")



app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,          # no cookies/Authorization in browser -> keep False
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
# ---------- Request Models (no bearer token needed) ----------
class UrlsRequest(BaseModel):
    patient_id: str
    page_no: int = 0

class SummaryRequest(BaseModel):
    patient_id: str
    page_no: int = 0
    max_docs: int = 15          # safety limit
    per_doc_max_chars: int = 40000  # avoid ballooning payload to LLM

@app.get("/healthz")
def health():
    return {"ok": True}

def eka_headers_server() -> Dict[str, str]:
    """Server-side headers using TokenManager auth."""
    h = {"Content-Type": "application/json"}
    h.update(eka_auth_header())
    return h

def fetch_appointments(patient_id: str, page_no: int = 0) -> Dict[str, Any]:
    url = f"{EKA_BASE_URL}/dr/v1/appointment"
    params = {"patient_id": patient_id, "page_no": page_no}
    r = requests.get(url, headers=eka_headers_server(), params=params, timeout=30)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=f"Eka API error: {r.text[:500]}")
    try:
        return r.json()
    except Exception:
        raise HTTPException(status_code=502, detail="Eka returned non-JSON")

def download_with_auth(url: str) -> bytes:
    """Download a document; if host is eka.care, include Authorization."""
    headers: Dict[str, str] = {}
    parsed = urlparse(url)
    if "eka.care" in (parsed.netloc or ""):
        headers.update(eka_auth_header())
    r = requests.get(url, headers=headers, timeout=60)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Failed to download: {url} ({r.status_code})")
    return r.content

# ---------- Endpoints ----------
@app.post("/api/prescription-urls")
def get_prescription_urls(req: UrlsRequest):
    data = fetch_appointments(req.patient_id, req.page_no)
    urls = extract_prescription_urls(data)
    return {
        "patient_id": req.patient_id,
        "count": len(urls),
        "urls": urls,
        "raw_sample": list(data)[:5] if isinstance(data, dict) else None
    }

# @app.post("/api/patient-summary")
# def patient_summary(req: SummaryRequest):
#     # 1) Discover URLs
#     data = fetch_appointments(req.patient_id, req.page_no)
#     urls = extract_prescription_urls(data)
#     if not urls:
#         return {
#             "patient_id": req.patient_id,
#             "summary": "No prescription/document URLs found in Eka response. Please verify the patient_id or API scopes.",
#             "timeline": [],
#             "key_findings": [],
#             "medications_mentioned": [],
#             "followups_or_actions": [],
#             "mental_state": {"color": "Amber", "explanation": "Insufficient data", "confidence": 0.2},
#             "debug": {"eka_keys": list(data.keys()) if isinstance(data, dict) else None}
#         }

#     # 2) Download + extract text (cap to max_docs)
#     texts: List[Dict[str, str]] = []
#     for i, url in enumerate(urls[: req.max_docs]):
#         try:
#             blob = download_with_auth(url)
#             text = pdf_bytes_to_text(blob, max_chars=req.per_doc_max_chars)
#             texts.append({"name": f"doc_{i+1}", "text": text})
#         except HTTPException as he:
#             texts.append({"name": f"doc_{i+1}", "text": f"[Download error for {url}: {he.detail}]"})
#         except Exception as e:
#             texts.append({"name": f"doc_{i+1}", "text": f"[Unhandled error retrieving {url}: {e}]"})

#     # 3) Summarize with Gemini
#     model = init_gemini()
#     result = summarize_patient_journey(model, texts, req.patient_id)

#     # 4) Attach debug context
#     result["_ingested_docs"] = len(texts)
#     result["_source_count"] = len(urls)
#     return result

@app.post("/api/patient-summary")
def patient_summary(req: SummaryRequest):
    # 1) Discover URLs (still quick)
    data = fetch_appointments(req.patient_id, req.page_no)
    urls = extract_prescription_urls(data)

    # 2) Initialize Gemini
    model = init_gemini()

    # 2a) DEMO FAST-PATH: if model is None (no/invalid key), SKIP downloads and return fallback now
    demo_mode = os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes")
    if demo_mode or model is None:
        from gemini_client import summarize_patient_journey
        result = summarize_patient_journey(None, [], req.patient_id)  # empty snippets -> fallback
        result["_ingested_docs"] = 0
        result["_source_count"] = len(urls)
        result["debug"] = {"note": "Demo fast-path: skipped downloads because no valid Gemini key"}
        return result

    # 3) (Real path) Download + extract text (cap to max_docs)
    texts: List[Dict[str, str]] = []
    for i, url in enumerate(urls[: req.max_docs]):
        try:
            blob = download_with_auth(url)
            text = pdf_bytes_to_text(blob, max_chars=req.per_doc_max_chars)
            texts.append({"name": f"doc_{i+1}", "text": text})
        except HTTPException as he:
            texts.append({"name": f"doc_{i+1}", "text": f"[Download error for {url}: {he.detail}]"})
        except Exception as e:
            texts.append({"name": f"doc_{i+1}", "text": f"[Unhandled error retrieving {url}: {e}]"})

    # 4) Summarize with Gemini
    result = summarize_patient_journey(model, texts, req.patient_id)
    result["_ingested_docs"] = len(texts)
    result["_source_count"] = len(urls)
    return result


@app.get("/api/prescription-urls")
def get_urls_get(patient_id: str = Query(...), page_no: int = Query(0)):
    data = fetch_appointments(patient_id, page_no)
    urls = extract_prescription_urls(data)
    return {"patient_id": patient_id, "count": len(urls), "urls": urls}

@app.get("/api/patient-summary")
def summary_get(patient_id: str = Query(...), page_no: int = Query(0),
                max_docs: int = Query(15), per_doc_max_chars: int = Query(40000)):
    req = SummaryRequest(
        patient_id=patient_id, page_no=page_no,
        max_docs=max_docs, per_doc_max_chars=per_doc_max_chars
    )
    return patient_summary(req)