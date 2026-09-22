import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { getStatus } from "../utils/api";

const POLL_INTERVAL_MS = 2000;

const STEP_ICONS = {
  "Transcribing":  "🎙️",
  "Detecting":     "🔇",
  "Extracting":    "🎞️",
  "Generating":    "🤖",
  "Merging":       "📝",
  "Burning":       "🎬",
  "Copying":       "📦",
  "Complete":      "✅",
  "Failed":        "❌",
};

function getStepIcon(step) {
  for (const [key, icon] of Object.entries(STEP_ICONS)) {
    if (step.startsWith(key)) return icon;
  }
  return "⚙️";
}

export default function ProcessingPage() {
  const { jobId } = useParams();
  const navigate = useNavigate();

  const [status, setStatus] = useState(null);
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState("");
  const pollRef = useRef(null);
  const logsEndRef = useRef(null);

  // Start polling
  useEffect(() => {
    const poll = async () => {
      try {
        const data = await getStatus(jobId);
        setStatus(data);

        // Add a log entry when step changes
        setLogs((prev) => {
          const last = prev[prev.length - 1];
          if (!last || last.step !== data.current_step) {
            return [...prev, { step: data.current_step, progress: data.progress_percent, ts: Date.now() }];
          }
          return prev;
        });

        if (data.status === "done") {
          clearInterval(pollRef.current);
          setTimeout(() => navigate(`/results/${jobId}`), 1200);
        }

        if (data.status === "failed") {
          clearInterval(pollRef.current);
          setError(data.error_message || "Processing failed.");
        }

      } catch (err) {
        setError(err.response?.data?.detail || "Lost connection to server.");
        clearInterval(pollRef.current);
      }
    };

    poll(); // Immediate first call
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);

    return () => clearInterval(pollRef.current);
  }, [jobId, navigate]);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const progress = status?.progress_percent ?? 0;
  const currentStep = status?.current_step ?? "Initializing…";
  const isDone = status?.status === "done";
  const isFailed = status?.status === "failed";

  return (
    <div className="max-w-2xl mx-auto px-6 py-16 animate-fade-in-up">
      <div className="text-center mb-10">
        <h1 className="font-display font-bold text-4xl text-white mb-2">
          Processing Your Video
        </h1>
        <p className="text-slate-500 font-mono text-sm">Job ID: {jobId}</p>
      </div>

      {/* ── Progress Ring + Status ── */}
      <div className="glass-card p-10 mb-6 text-center">
        {/* Circular progress */}
        <div className="relative w-36 h-36 mx-auto mb-8">
          <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
            {/* Track */}
            <circle cx="50" cy="50" r="42" fill="none" stroke="#162038" strokeWidth="8" />
            {/* Progress */}
            <circle
              cx="50" cy="50" r="42"
              fill="none"
              stroke={isDone ? "#10b981" : isFailed ? "#f43f5e" : "url(#prog-gradient)"}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={`${2 * Math.PI * 42}`}
              strokeDashoffset={`${2 * Math.PI * 42 * (1 - progress / 100)}`}
              style={{ transition: "stroke-dashoffset 0.6s ease" }}
            />
            <defs>
              <linearGradient id="prog-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#2259f5" />
                <stop offset="100%" stopColor="#00d4ff" />
              </linearGradient>
            </defs>
          </svg>
          {/* Center content */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            {isDone ? (
              <CheckCircle2 size={32} className="text-accent-emerald" />
            ) : isFailed ? (
              <AlertCircle size={32} className="text-accent-rose" />
            ) : (
              <>
                <span className="font-display font-bold text-2xl text-white">{progress}%</span>
                <Loader2 size={14} className="text-slate-500 mt-1 animate-spin" />
              </>
            )}
          </div>
        </div>

        {/* Current step */}
        <div className="flex items-center justify-center gap-2 mb-2">
          <span className="text-xl">{getStepIcon(currentStep)}</span>
          <p className="font-display font-semibold text-white text-lg">{currentStep}</p>
        </div>

        {isDone && (
          <p className="text-accent-emerald text-sm">
            Complete! Redirecting to results…
          </p>
        )}
      </div>

      {/* ── Error ── */}
      {error && (
        <div className="flex items-start gap-3 p-4 rounded-xl bg-rose-950 bg-opacity-40 border border-accent-rose border-opacity-30 mb-6">
          <AlertCircle size={18} className="text-accent-rose flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-rose-300 font-semibold text-sm">Processing Failed</p>
            <p className="text-rose-400 text-sm mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* ── Pipeline Steps ── */}
      <div className="glass-card p-6">
        <h3 className="font-display font-semibold text-slate-300 text-sm mb-4 uppercase tracking-wider">
          Pipeline Log
        </h3>
        <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
          {logs.map((log, i) => (
            <div
              key={i}
              className="flex items-center gap-3 py-2 border-b border-white border-opacity-5 last:border-0"
            >
              <span className="text-base">{getStepIcon(log.step)}</span>
              <span className="text-slate-300 text-sm flex-1">{log.step}</span>
              <span className="font-mono text-xs text-slate-600">{log.progress}%</span>
            </div>
          ))}
          {logs.length === 0 && (
            <p className="text-slate-600 text-sm text-center py-4">Waiting for pipeline to start…</p>
          )}
          <div ref={logsEndRef} />
        </div>
      </div>

      {/* Tip */}
      <p className="text-center text-slate-600 text-xs mt-6">
        Large videos may take several minutes. BLIP and Whisper models run locally.
      </p>
    </div>
  );
}
