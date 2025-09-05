# Frontend — Patient Journey Summarizer (React + Vite + Tailwind)

## What this app does
- Takes a patient's OID (`patient_id`) and an **Eka Bearer token** (for prototype use only).
- Calls the backend to:
  1) Discover prescription/document URLs
  2) Generate a **Patient Journey** summary via Gemini
- Displays the summary, timeline, key findings, and a color-coded **mental state** badge.

## Setup

```bash
cd frontend
npm install
npm run dev
```

The app assumes the backend runs at `http://localhost:8000`. You can override via `VITE_API_BASE` in `.env`:

```bash
echo "VITE_API_BASE=http://localhost:8000" > .env
```

## Security Note
Do not expose Eka tokens in a real production frontend. Use a secure server-side flow instead.
