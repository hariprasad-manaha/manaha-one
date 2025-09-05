import React from "react";

type Props = {
  progress: number;        // 0..100
  label?: string;          // optional text like "Summarizing..."
  visible: boolean;        // show/hide overlay
};

export default function LoadingOverlay({ progress, label, visible }: Props) {
  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur">
      <div className="w-full max-w-sm px-6 py-6 rounded-2xl border border-white/15 bg-white/10 shadow-xl">
        <div className="flex items-center justify-between mb-3">
          <div className="text-sm text-white/70">{label || "Loading..."}</div>
          <div className="text-sm text-white/60">{progress}%</div>
        </div>

        {/* Progress bar */}
        <div className="h-2 w-full bg-white/15 rounded-full overflow-hidden">
          <div
            className="h-2 rounded-full transition-all"
            style={{
              width: `${progress}%`,
              // color changes slightly by progress
              background:
                progress < 50
                  ? "linear-gradient(90deg, #93c5fd, #60a5fa)"
                  : progress < 80
                  ? "linear-gradient(90deg, #34d399, #10b981)"
                  : "linear-gradient(90deg, #f59e0b, #f97316)",
            }}
          />
        </div>

        {/* Big circular indicator with percentage */}
        <div className="mt-6 flex items-center justify-center">
          <div className="relative w-28 h-28">
            <div className="absolute inset-0 rounded-full border-4 border-white/15" />
            <div
              className="absolute inset-0 rounded-full border-4"
              style={{
                borderColor: "transparent",
                borderTopColor: "rgba(255,255,255,0.8)",
                transform: `rotate(${(progress / 100) * 360}deg)`,
                transition: "transform 200ms linear",
              }}
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-2xl font-semibold">{progress}%</div>
            </div>
          </div>
        </div>

        <div className="mt-4 text-center text-xs text-white/60">
          This may take a few seconds depending on document size.
        </div>
      </div>
    </div>
  );
}