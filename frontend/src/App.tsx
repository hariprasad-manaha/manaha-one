import React, { useEffect, useRef, useState } from "react";
import MentalStateCard from "./components/MentalStateCard";
import LoadingOverlay from "./components/LoadingOverlay";
import Toast from "./components/Toast";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

type UrlsResponse = {
  patient_id: string;
  count: number;
  urls: string[];
};

type MentalState = {
  color: "Green" | "Amber" | "Red";
  explanation: string;
  confidence: number; // 0..1
};

type SummaryResponse = {
  patient_id: string;
  summary: string;
  timeline: { date: string | null; title: string; details: string }[];
  key_findings: string[];
  medications_mentioned: string[];
  followups_or_actions: string[];
  mental_state: MentalState;
  _ingested_docs?: number;
  _source_count?: number;
  debug?: any;
  _raw?: string;
};

// Smooth fake progress controller: rises to ~90% while waiting, then completes to 100%.
function useProgress() {
  const [visible, setVisible] = useState(false);
  const [label, setLabel] = useState<string>("Loading...");
  const [progress, setProgress] = useState(0);
  const timerRef = useRef<number | null>(null);

  function start(newLabel: string) {
    setLabel(newLabel);
    setVisible(true);
    setProgress(0);

    if (timerRef.current) window.clearInterval(timerRef.current);

    timerRef.current = window.setInterval(() => {
      setProgress((p) => {
        if (p >= 90) return p; // hold near completion until complete()
        const bump = Math.random() * 6 + 3; // 3..9
        return Math.min(90, p + bump);
      });
    }, 250);
  }

  function complete() {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setProgress(100);
    setTimeout(() => setVisible(false), 400);
    setTimeout(() => setProgress(0), 600);
  }

  function fail() {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setProgress((p) => (p < 95 ? 95 : p));
    setTimeout(() => setVisible(false), 500);
    setTimeout(() => setProgress(0), 600);
  }

  useEffect(() => {
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, []);

  return { visible, label, progress, start, complete, fail };
}
// helper at top of file (below imports)
async function fetchWithTimeout(input: RequestInfo | URL, init: RequestInit = {}, timeoutMs = 20000) {
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(input, { ...init, signal: controller.signal });
    return res;
  } finally {
    clearTimeout(t);
  }
}

export default function App() {
  const [patientId, setPatientId] = useState("");
  const [urls, setUrls] = useState<string[]>([]);
  const [result, setResult] = useState<SummaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState("");

  const discoverLoader = useProgress();
  const summarizeLoader = useProgress();

  function showToast(msg: string) {
    setToastMsg(msg);
  }

  async function discoverUrls() {
    if (!patientId.trim()) {
      showToast("⚠️ Please enter a Patient OID before proceeding.");
      return; // do NOT start loader
    }
    setError(null);
    setUrls([]);
    discoverLoader.start("Finding prescription URLs...");
    try {
      const r = await fetch(`${API_BASE}/api/prescription-urls`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patient_id: patientId }),
      });
      const text = await r.text();
      if (!r.ok) throw new Error(text);
      const data: UrlsResponse = JSON.parse(text);
      setUrls(data.urls || []);
      discoverLoader.complete();
    } catch (e: any) {
      setError(e?.message || "Failed to fetch URLs");
      discoverLoader.fail();
    }
  }

  async function summarize() {
    if (!patientId.trim()) {
      showToast("⚠️ Please enter a Patient OID before summarizing.");
      return; // do NOT start loader
    }
    setError(null);
    setResult(null);
    summarizeLoader.start("Summarizing the patient’s journey...");
    try {
      const r = await fetch(`${API_BASE}/api/patient-summary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patient_id: patientId }),
      });
      const text = await r.text();
      if (!r.ok) throw new Error(text);
      const data = JSON.parse(text) as SummaryResponse;
      setResult(data);
      summarizeLoader.complete();
    } catch (e: any) {
      setError(e?.message || "Something went wrong");
      summarizeLoader.fail();
    }
  }

  const buttonsDisabled = !patientId.trim();

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* Toast */}
      <Toast message={toastMsg} show={!!toastMsg} onClose={() => setToastMsg("")} />

      {/* Loading overlays */}
      <LoadingOverlay
        visible={discoverLoader.visible}
        label={discoverLoader.label}
        progress={Math.round(discoverLoader.progress)}
      />
      <LoadingOverlay
        visible={summarizeLoader.visible}
        label={summarizeLoader.label}
        progress={Math.round(summarizeLoader.progress)}
      />

      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Manaha One</h1>
        <div className="text-sm text-white/60">Prototype • Do not use for diagnosis</div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left panel: inputs */}
        <div className="card p-5 space-y-4">
          <div className="space-y-2">
            <label className="label">Patient OID (patient_id)</label>
            <input
              className="input"
              placeholder="e.g., 175050134757165"
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
            />
          </div>

          <div className="flex gap-3">
            <button
              className={`btn btn-primary ${buttonsDisabled ? "opacity-50 cursor-not-allowed" : ""}`}
              onClick={discoverUrls}
              disabled={buttonsDisabled}
            >
              Discover Prescriptions
            </button>
            <button
              className={`btn bg-indigo-600 hover:bg-indigo-700 text-white ${buttonsDisabled ? "opacity-50 cursor-not-allowed" : ""}`}
              onClick={summarize}
              disabled={buttonsDisabled}
            >
              Summarize Journey
            </button>
          </div>

          {error && (
            <div className="bg-red-500/20 border border-red-500/40 text-red-200 rounded-xl px-3 py-2">
              {error}
            </div>
          )}

          {urls.length > 0 && (
            <div className="mt-2">
              <div className="label mb-1">Found {urls.length} document link(s)</div>
              <ul className="list-disc list-inside space-y-1 text-sm text-white/80">
                {urls.map((u, i) => (
                  <li key={i}>
                    <a className="underline" href={u} target="_blank" rel="noreferrer">
                      {u}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Right panel: Mental state */}
        <MentalStateCard mentalState={result?.mental_state} />
      </div>

      {/* Patient Journey */}
      <div className="card p-5 space-y-6">
        <h2 className="text-xl font-semibold">Patient Journey</h2>
        {!result && <div className="text-white/60">Run a summary to view results.</div>}
        {result && (
          <div className="space-y-6">
            <div>
              <h3 className="font-medium mb-2">Summary</h3>
              <p className="text-white/80 whitespace-pre-wrap">{result.summary}</p>
            </div>

            <div>
              <h3 className="font-medium mb-2">Timeline</h3>
              {result.timeline?.length ? (
                <ol className="space-y-2">
                  {result.timeline.map((t, i) => (
                    <li key={i} className="flex gap-3 items-start">
                      <div className="mt-1">
                        <span className="inline-block w-2 h-2 rounded-full bg-white/40" />
                      </div>
                      <div>
                        <div className="text-white/90 font-medium">
                          {t.date || "Unknown date"} — {t.title}
                        </div>
                        <div className="text-white/70 text-sm">{t.details}</div>
                      </div>
                    </li>
                  ))}
                </ol>
              ) : (
                <div className="text-white/60">No timeline items.</div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="font-medium mb-2">Key Findings</h3>
                {result.key_findings?.length ? (
                  <ul className="list-disc list-inside text-white/80 space-y-1">
                    {result.key_findings.map((k, i) => (
                      <li key={i}>{k}</li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-white/60">None extracted.</div>
                )}
              </div>
              <div>
                <h3 className="font-medium mb-2">Medications Mentioned</h3>
                {result.medications_mentioned?.length ? (
                  <ul className="list-disc list-inside text-white/80 space-y-1">
                    {result.medications_mentioned.map((k, i) => (
                      <li key={i}>{k}</li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-white/60">None extracted.</div>
                )}
              </div>
            </div>

            <div>
              <h3 className="font-medium mb-2">Follow-ups / Actions</h3>
              {result.followups_or_actions?.length ? (
                <ul className="list-disc list-inside text-white/80 space-y-1">
                  {result.followups_or_actions.map((k, i) => (
                    <li key={i}>{k}</li>
                  ))}
                </ul>
              ) : (
                <div className="text-white/60">None extracted.</div>
              )}
            </div>

            {result._raw && (
              <details className="bg-white/5 border border-white/10 rounded-xl p-3">
                <summary className="cursor-pointer">Raw LLM Output</summary>
                <pre className="text-xs whitespace-pre-wrap">{result._raw}</pre>
              </details>
            )}
          </div>
        )}
      </div>
    </div>
  );
}