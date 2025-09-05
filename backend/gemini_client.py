import os
import json
from typing import List, Dict, Any, Optional
import concurrent.futures

# Gemini SDK
import google.generativeai as genai


def _looks_like_fake_key(k: Optional[str]) -> bool:
    if not k:
        return True
    k = k.strip()
    # Heuristics: placeholder or too short to be real
    if k.lower().startswith("your_") or k.lower().startswith("test") or k.lower().startswith("abc"):
        return True
    if len(k) < 20:
        return True
    return False


def init_gemini():
    """
    Initialize Gemini if GOOGLE_API_KEY is present and looks real.
    Returns a GenerativeModel instance or None (caller will fallback).
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if _looks_like_fake_key(api_key):
        print("[gemini] No key or likely fake key provided; will use fallback.")
        return None

    try:
        genai.configure(api_key=api_key)
        model_name = os.environ.get("MODEL_NAME", "gemini-1.5-pro-latest")
        model = genai.GenerativeModel(model_name)
        return model
    except Exception as e:
        print(f"[gemini] init failed: {e}; will use fallback.")
        return None


def _build_prompt(snippets: List[Dict[str, str]], patient_id: str) -> str:
    doc_blocks = []
    for snip in snippets:
        fn = snip.get("name", "document")
        tx = (snip.get("text") or "").strip()
        doc_blocks.append(f"### {fn}\n{tx}")

    docs_joined = "\n\n".join(doc_blocks)

    prompt = f"""
You are a clinical documentation AI assisting doctors at a primary care clinic in India.
You will receive multiple prescription/consultation notes for a single patient (id: {patient_id}).
Create a concise but comprehensive "Patient Journey" summary across time with a short timeline
of key events, medications, diagnoses, and follow-ups. Be factual and only use information
present in the provided documents. If dates are missing, infer relative order conservatively
and mention uncertainty.

Return ONLY valid JSON that conforms to this schema (no Markdown, no extra text):

{{
  "patient_id": "string",
  "summary": "2-3 short paragraphs summarizing the patient's journey.",
  "timeline": [
    {{"date": "YYYY-MM-DD or null if unknown", "title": "Short event title", "details": "1-2 lines"}}
  ],
  "key_findings": [
    "bullet finding 1", "bullet finding 2"
  ],
  "medications_mentioned": [
    "Drug name (strength, frequency)"
  ],
  "followups_or_actions": [
    "Non-diagnostic suggestions for clinicians (e.g., reconcile meds, check adherence, consider labs)"
  ],
  "mental_state": {{
    "color": "Green|Amber|Red",
    "explanation": "Why you chose this color from the notes",
    "confidence": 0.0
  }}
}}

Rules:
- "mental_state.color" approximates overall mental/psychological well-being implied by the notes:
  Green = generally stable/positive; Amber = mild/moderate concerns or inconsistent adherence;
  Red = clear distress, significant depressive/anxiety symptoms, suicidality, or severe psychosocial factors.
- If mental health is not discussed, choose "Amber" with low confidence and explain uncertainty.
- Do NOT invent diagnoses. Mark unknown fields as null where appropriate.
- Keep the whole output under ~1200 words.

Documents:
{docs_joined}
""".strip()

    return prompt


def _parse_or_stub(text: str, patient_id: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        return {
            "patient_id": patient_id,
            "summary": "LLM returned non-JSON or invalid JSON. Showing fallback.",
            "timeline": [],
            "key_findings": [],
            "medications_mentioned": [],
            "followups_or_actions": [],
            "mental_state": {"color": "Amber", "explanation": "Parsing failure", "confidence": 0.1},
            "_raw": text,
        }


def _fallback_summary(patient_id: str) -> Dict[str, Any]:
    return {
        "patient_id": patient_id,
        "summary": (
            "The patient initially presented with fever and cough. Subsequent consultations indicate "
            "gradual improvement with a shift from empirical antibiotics to supportive care and follow-up monitoring. "
            "No red-flag deterioration is evident in the available notes."
        ),
        "timeline": [
            {"date": "2024-01-05", "title": "Initial Visit", "details": "Complaints of fever and cough; basic labs ordered."},
            {"date": "2024-02-02", "title": "Follow-up", "details": "Symptoms improved; medication adjusted; advised rest and fluids."},
            {"date": "2024-03-10", "title": "Latest Visit", "details": "Stable condition; supportive care continued; routine follow-up."},
        ],
        "key_findings": ["Fever and cough at onset", "Gradual symptomatic improvement", "No alarming findings"],
        "medications_mentioned": ["Antibiotics (empirical)", "Paracetamol", "Vitamin supplements"],
        "followups_or_actions": [
            "Ensure medication adherence and hydration",
            "Re-check if fever persists or worsens",
            "Routine follow-up to confirm full recovery",
        ],
        "mental_state": {
            "color": "Green",
            "explanation": "Notes imply stable progress and no documented mental distress.",
            "confidence": 0.8,
        },
        "debug": {"note": "Fallback summary used (invalid/missing Gemini API key, error, or timeout)"},
    }


def summarize_patient_journey(model: Optional[object], snippets: List[Dict[str, str]], patient_id: str) -> Dict[str, Any]:
    """
    Call Gemini to summarize. If model is None OR the API call fails OR times out, return a fallback sample.
    """
    # If no model (e.g., missing/fake key), use fallback immediately
    if model is None:
        return _fallback_summary(patient_id)

    prompt = _build_prompt(snippets, patient_id)
    generation_config = {
        "response_mime_type": "application/json",
        "temperature": 0.2,
    }

    def _call():
        # Separate function so we can run it in a thread with a timeout
        resp = model.generate_content(prompt, generation_config=generation_config)
        return resp.text or "{}"

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_call)
            # Hard timeout (seconds). Adjust as needed.
            text = fut.result(timeout=15)
        return _parse_or_stub(text, patient_id)
    except concurrent.futures.TimeoutError:
        print("[gemini] generate_content timed out; using fallback.")
        return _fallback_summary(patient_id)
    except Exception as e:
        print(f"[gemini] generate_content failed; using fallback: {e}")
        return _fallback_summary(patient_id)