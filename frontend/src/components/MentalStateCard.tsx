import React from "react";

type MentalState = {
  color: "Green" | "Amber" | "Red";
  explanation: string;
  confidence: number; // 0..1
};

type Props = {
  mentalState?: MentalState | null;
};

function Dot({ color }: { color: MentalState["color"] }) {
  const map: Record<MentalState["color"], string> = {
    Green: "bg-green-400",
    Amber: "bg-amber-400",
    Red: "bg-rose-500",
  };
  return <span className={`inline-block w-2.5 h-2.5 rounded-full ${map[color]}`} />;
}

function gradient(color: MentalState["color"]) {
  switch (color) {
    case "Green":
      return "from-emerald-500/40 via-emerald-600/30 to-emerald-700/30";
    case "Amber":
      return "from-amber-400/40 via-amber-500/30 to-orange-600/30";
    case "Red":
      return "from-rose-500/40 via-rose-600/30 to-rose-700/30";
  }
}

function chipClasses(color: MentalState["color"]) {
  switch (color) {
    case "Green":
      return "bg-emerald-500/20 text-emerald-200 border-emerald-400/40";
    case "Amber":
      return "bg-amber-500/20 text-amber-100 border-amber-400/40";
    case "Red":
      return "bg-rose-500/20 text-rose-100 border-rose-400/40";
  }
}

export default function MentalStateCard({ mentalState }: Props) {
  if (!mentalState) {
    return (
      <div className="card p-5">
        <h2 className="font-medium mb-3">Mental State (LLM-estimated)</h2>
        <div className="text-white/60">Run a summary to estimate mental state.</div>
      </div>
    );
  }

  const pct = Math.max(0, Math.min(100, Math.round(mentalState.confidence * 100)));

  return (
    <div
      className={`card overflow-hidden p-0 border-white/10`}
      aria-live="polite"
    >
      {/* gradient header */}
      <div className={`p-5 bg-gradient-to-br ${gradient(mentalState.color)} relative`}>
        <div className="absolute inset-0 bg-white/5 pointer-events-none" />
        <div className="relative flex items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="text-xs uppercase tracking-wider text-white/70">
              Mental State (LLM-estimated)
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`badge border ${chipClasses(mentalState.color)} backdrop-blur`}
              >
                <Dot color={mentalState.color} />
                <span className="font-semibold">{mentalState.color}</span>
              </span>
            </div>
          </div>
          {/* big subtle watermark dot */}
          <div className="w-12 h-12 rounded-full bg-white/10 backdrop-blur-sm border border-white/20" />
        </div>
      </div>

      {/* body */}
      <div className="p-5 space-y-4">
        <p className="text-white/85 leading-relaxed">{mentalState.explanation}</p>

        {/* confidence bar */}
        <div>
          <div className="flex items-end justify-between mb-1">
            <span className="text-sm text-white/70">Confidence</span>
            <span className="text-sm text-white/70">{pct}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-white/10 overflow-hidden">
            <div
              className={`h-2 rounded-full transition-all duration-500 ${
                mentalState.color === "Green"
                  ? "bg-emerald-400"
                  : mentalState.color === "Amber"
                  ? "bg-amber-400"
                  : "bg-rose-500"
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* quick legend */}
        <div className="text-xs text-white/50 mt-1">
          <span className="mr-2">Legend:</span>
          <span className="mr-3"><span className="inline-block w-2 h-2 rounded-full bg-emerald-400 mr-1" />Green = stable/positive</span>
          <span className="mr-3"><span className="inline-block w-2 h-2 rounded-full bg-amber-400 mr-1" />Amber = mild/moderate concerns</span>
          <span className="mr-3"><span className="inline-block w-2 h-2 rounded-full bg-rose-500 mr-1" />Red = significant distress</span>
        </div>
      </div>
    </div>
  );
}