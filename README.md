# Patient Journey Summarizer (Eka Care + Gemini)

Full-stack web app to ingest a patient's prescription documents from **Eka Care** and produce a
**Patient Journey** summary via **Google Gemini**, including an estimated **mental state** color (Green/Amber/Red).

## Project Structure
```
patient-journey-summarizer/
├─ backend/      # FastAPI service: fetch Eka docs, parse PDFs, call Gemini
└─ frontend/     # React + Vite UI: input patient id & token, display results
```

## Quickstart

1) Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # add GOOGLE_API_KEY
uvicorn main:app --reload --port 8000
```

2) Frontend
```bash
cd frontend
npm install
npm run dev
```

3) Use the app
- Open the frontend (Vite will print the local URL, usually http://localhost:5173).
- Enter the **patient OID** and an **Eka Bearer token** (prototype).
- Click **Discover Prescription URLs** (optional) then **Summarize Journey**.

## Deployment Notes
- **Backend**: Containerize and deploy to Cloud Run/App Engine. Store secrets in Secret Manager.
- **Gemini**: The `GOOGLE_API_KEY` should be configured as a secret, not embedded in code.
- **Eka tokens**: For production, authenticate **server-to-server**. Do not send tokens from the browser.
- Add logging/observability; consider a background job for long documents.

## Legal/Safety
- This tool helps clinicians, but is **not** a medical device. It must not replace clinical judgment.
- Mental state color is an **estimate from text**. Confirm with the patient and clinician-led screening tools.

### Update: Server-Side Eka Auth
- Configure `.env` in `backend/` with `EKA_API_KEY`, `EKA_CLIENT_ID`, `EKA_CLIENT_SECRET`, `EKA_USER_TOKEN`.
- Frontend no longer collects any Eka token.
