import React, { useEffect } from "react";

type ToastProps = {
  message: string;
  show: boolean;
  onClose: () => void;
  duration?: number; // ms
};

export default function Toast({ message, show, onClose, duration = 2500 }: ToastProps) {
  useEffect(() => {
    if (!show) return;
    const timer = setTimeout(onClose, duration);
    return () => clearTimeout(timer);
  }, [show, duration, onClose]);

  if (!show) return null;

  return (
    <div className="fixed top-5 right-5 z-50">
      <div className="px-4 py-3 rounded-xl bg-red-600 text-white shadow-lg animate-fade-in-up">
        {message}
      </div>
    </div>
  );
}