# Backend — Patient Journey Summarizer (FastAPI + Gemini)

## What this service does
- Accepts a patient's OID (`patient_id`) and an Eka Care **Bearer token** (temporarily, for this prototype).
- Calls Eka Care appointment API to discover **prescription document URLs** (best-effort scanning for PDF/clinical doc links).
- Downloads and extracts text from those prescription PDFs.
- Sends the extracted text to **Google Gemini** to produce:
  - A **patient journey** summary
  - A timeline of key events
  - Key findings & recommendations (non-diagnostic)
  - A **mental state color** (Green/Amber/Red) with explanation

> ⚠️ Security note: In production, do **not** send Eka tokens from the browser.
> Store them server-side (e.g., service account, secrets manager) and scope appropriately.
> This prototype accepts the token via request body for ease of testing.

## Prerequisites
- **Python 3.10+**
- A **Google AI Studio** API key with access to Gemini models.
  - Create one at: https://aistudio.google.com/
- Your **Eka Care** API token and the `patient_id` (OID).

## Setup
1) Create a virtualenv and install requirements:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2) Copy `.env.example` to `.env` and fill values:

```bash
cp .env.example .env
# Edit .env to add GOOGLE_API_KEY, optionally adjust MODEL_NAME
```

3) Run the API:

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000` and docs at `http://localhost:8000/docs`.

## Key Endpoints

- `POST /api/prescription-urls`
  - Body: `{ "patient_id": "...", "eka_bearer_token": "..." }`
  - Returns: discovered prescription/document URLs (best-effort)

- `POST /api/patient-summary`
  - Body: `{ "patient_id": "...", "eka_bearer_token": "..." }`
  - Runs full pipeline: fetch URLs -> download -> extract -> Gemini summary

## Notes on Eka API Response Variability
The demo uses **best-effort URL discovery** because different tenants/versions may nest document links in
different shapes (`documents`, `prescriptions`, `attachments`, `files`, etc.).
The `extract_prescription_urls` function recursively scans for:
- keys like `url`, `file_url`, `prescription_url`, `download_url`
- PDF links (`.pdf`) and strings containing `rx`, `prescription`, or `consult` (case-insensitive)

If your JSON structure is known, you can replace that extractor with direct, explicit field access.

## Disclaimer
This system provides **summaries** and **non-diagnostic** recommendations to help clinicians triage and
understand patient journeys. It is **not** a medical device and must not replace clinical judgment.

---

## Server-side Eka Auth (Updated)
This service now uses **Connect Login** to obtain access & refresh tokens using
`EKA_API_KEY`, `EKA_CLIENT_ID`, `EKA_CLIENT_SECRET`, and `EKA_USER_TOKEN` from `.env`.
Tokens are cached in memory and **auto-refreshed** via **Connect Refresh V2**.

Frontend no longer needs the Eka Bearer token.
