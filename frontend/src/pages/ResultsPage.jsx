import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Download, Film, FileText, FileCode2, CheckCircle,
  AlertCircle, Clock, Globe, RefreshCw, MessageSquare,
  Eye, X, Play, ChevronDown, ChevronUp
} from "lucide-react";
import { getResult, getDownloadUrls } from "../utils/api";

export default function ResultsPage() {
  const { jobId } = useParams();
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("all");
  const [preview, setPreview] = useState(null); // { type: 'video'|'srt'|'transcript', content, url }
  const [srtText, setSrtText] = useState("");
  const [transcriptText, setTranscriptText] = useState("");
  const urls = getDownloadUrls(jobId);

  useEffect(() => {
    getResult(jobId).then(setResult).catch(e => setError(e.response?.data?.detail || "Failed to load results."));
  }, [jobId]);

  // Pre-fetch text file contents for preview
  useEffect(() => {
    if (!result) return;
    fetch(urls.srt).then(r => r.text()).then(setSrtText).catch(() => {});
    fetch(urls.transcript).then(r => r.text()).then(setTranscriptText).catch(() => {});
  }, [result]);

  if (error) return (
    <div className="max-w-2xl mx-auto px-6 py-16 text-center">
      <AlertCircle size={48} className="text-accent-rose mx-auto mb-4" />
      <h2 className="font-display font-bold text-2xl text-white mb-2">Results Unavailable</h2>
      <p className="text-slate-400 mb-8">{error}</p>
      <Link to="/upload" className="btn-primary inline-flex items-center gap-2"><RefreshCw size={16} /> Try Again</Link>
    </div>
  );

  if (!result) return (
    <div className="max-w-2xl mx-auto px-6 py-32 text-center">
      <div className="w-10 h-10 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
      <p className="text-slate-400">Loading results…</p>
    </div>
  );

  const speechEntries = result.subtitle_entries.filter(e => !e.is_explainer);
  const explainerEntries = result.subtitle_entries.filter(e => e.is_explainer);
  const filteredEntries = activeTab === "speech" ? speechEntries : activeTab === "explainers" ? explainerEntries : result.subtitle_entries;

  return (
    <div className="max-w-5xl mx-auto px-6 py-16 animate-fade-in-up">

      {/* Preview Modal */}
      {preview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-80 backdrop-blur-sm">
          <div className="relative w-full max-w-3xl glass-card p-6 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display font-bold text-white text-lg">{preview.title}</h3>
              <div className="flex items-center gap-3">
                <a
                  href={preview.downloadUrl}
                  download={preview.filename}
                  className="btn-primary flex items-center gap-2 text-sm py-2 px-4"
                >
                  <Download size={14} /> Download
                </a>
                <button onClick={() => setPreview(null)} className="text-slate-400 hover:text-white transition-colors">
                  <X size={22} />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-auto">
              {preview.type === "video" && (
                <video
                  src={preview.url}
                  controls
                  autoPlay
                  className="w-full rounded-xl bg-black"
                  style={{ maxHeight: "60vh" }}
                />
              )}
              {(preview.type === "srt" || preview.type === "transcript") && (
                <pre className="text-slate-300 text-sm font-mono whitespace-pre-wrap leading-relaxed p-4 bg-surface-900 rounded-xl overflow-auto" style={{ maxHeight: "65vh" }}>
                  {preview.content}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between mb-10 flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle size={20} className="text-accent-emerald" />
            <span className="text-accent-emerald font-body font-medium text-sm">Processing Complete</span>
          </div>
          <h1 className="font-display font-bold text-4xl text-white">Your Results</h1>
          <p className="text-slate-500 font-mono text-xs mt-1">Job: {jobId}</p>
        </div>
        <Link to="/upload" className="btn-ghost flex items-center gap-2 text-sm">
          <RefreshCw size={14} /> Process Another
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard icon={<Clock size={16} />} label="Duration" value={formatDuration(result.duration_seconds)} />
        <StatCard icon={<Globe size={16} />} label="Language" value={result.language_detected?.toUpperCase() || "—"} />
        <StatCard icon={<MessageSquare size={16} />} label="Speech Lines" value={speechEntries.length} />
        <StatCard icon={<Eye size={16} />} label="Scene Explainers" value={explainerEntries.length} />
      </div>

      {/* Scene explainers tip */}
      {explainerEntries.length === 0 && (
        <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-950 bg-opacity-30 border border-amber-500 border-opacity-20 mb-6 text-sm">
          <Eye size={16} className="text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-amber-300 font-semibold">No scene explainers generated</p>
            <p className="text-amber-500 mt-1">
              This video had no segments quiet enough to trigger BLIP scene captioning.
              Try re-uploading with a <strong className="text-amber-400">higher silence threshold</strong> (e.g. −30 dB)
              and <strong className="text-amber-400">lower minimum silence duration</strong> (e.g. 0.5s) in Processing Options.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Downloads */}
        <div className="space-y-4">
          <h2 className="font-display font-semibold text-white text-lg">Preview & Download</h2>

          <PreviewCard
            icon={<Film size={20} />}
            label="Processed Video"
            description="MP4 with burned-in subtitles"
            color="brand"
            onPreview={() => setPreview({
              type: "video",
              title: "Processed Video",
              url: urls.video,
              downloadUrl: urls.video,
              filename: `subtitled_${jobId}.mp4`,
            })}
            downloadUrl={urls.video}
            filename={`subtitled_${jobId}.mp4`}
          />
          <PreviewCard
            icon={<FileCode2 size={20} />}
            label="SRT Subtitles"
            description="Standard subtitle file"
            color="cyan"
            onPreview={() => setPreview({
              type: "srt",
              title: "SRT Subtitles",
              content: srtText || "Loading…",
              downloadUrl: urls.srt,
              filename: `${jobId}.srt`,
            })}
            downloadUrl={urls.srt}
            filename={`${jobId}.srt`}
          />
          <PreviewCard
            icon={<FileText size={20} />}
            label="Transcript"
            description="Plain text, no timestamps"
            color="violet"
            onPreview={() => setPreview({
              type: "transcript",
              title: "Plain Text Transcript",
              content: transcriptText || "Loading…",
              downloadUrl: urls.transcript,
              filename: `${jobId}_transcript.txt`,
            })}
            downloadUrl={urls.transcript}
            filename={`${jobId}_transcript.txt`}
          />

          <div className="glass-card p-4 text-center">
            <p className="text-slate-500 text-xs">Processed in</p>
            <p className="font-display font-bold text-white text-xl mt-1">{result.processing_time_seconds.toFixed(1)}s</p>
          </div>
        </div>

        {/* Subtitle Preview */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display font-semibold text-white text-lg">
              Subtitle Preview
              <span className="ml-2 text-sm text-slate-500 font-body font-normal">({result.subtitle_entries.length} entries)</span>
            </h2>
          </div>

          <div className="flex gap-2 mb-4">
            {[
              { key: "all", label: "All" },
              { key: "speech", label: `Speech (${speechEntries.length})` },
              { key: "explainers", label: `Explainers (${explainerEntries.length})` },
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-1.5 rounded-lg text-sm transition-all duration-200 ${activeTab === tab.key ? "bg-brand-600 text-white" : "bg-surface-700 text-slate-400 hover:text-white"}`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="glass-card p-4 max-h-[520px] overflow-y-auto space-y-2">
            {filteredEntries.length === 0 ? (
              <p className="text-slate-600 text-sm text-center py-8">No entries in this category.</p>
            ) : (
              filteredEntries.map(entry => (
                <div key={entry.index} className={entry.is_explainer ? "subtitle-explainer" : "subtitle-speech"}>
                  <div className="flex items-start gap-3">
                    <span className="font-mono text-xs text-slate-600 mt-0.5 flex-shrink-0 w-5">{entry.index}</span>
                    <div className="flex-1">
                      <p className="text-xs font-mono text-slate-500 mb-0.5">
                        {formatSRTTime(entry.start_time)} → {formatSRTTime(entry.end_time)}
                      </p>
                      <p className={entry.is_explainer ? "text-accent-cyan" : "text-slate-200"}>{entry.text}</p>
                    </div>
                    {entry.is_explainer && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-900 bg-opacity-40 text-accent-cyan flex-shrink-0">AI</span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ──

function StatCard({ icon, label, value }) {
  return (
    <div className="glass-card p-4 text-center">
      <div className="flex items-center justify-center gap-1.5 text-slate-500 text-xs mb-1">{icon} {label}</div>
      <p className="font-display font-bold text-white text-xl">{value}</p>
    </div>
  );
}

const COLORS = {
  brand:  { bg: "bg-brand-600 bg-opacity-20", icon: "text-brand-400", hover: "hover:border-brand-500" },
  cyan:   { bg: "bg-cyan-900 bg-opacity-20",  icon: "text-accent-cyan", hover: "hover:border-accent-cyan" },
  violet: { bg: "bg-violet-900 bg-opacity-20", icon: "text-accent-violet", hover: "hover:border-accent-violet" },
};

function PreviewCard({ icon, label, description, color, onPreview, downloadUrl, filename }) {
  const c = COLORS[color] || COLORS.brand;
  return (
    <div className={`glass-card border border-white border-opacity-5 ${c.hover} transition-all duration-300 overflow-hidden`}>
      <div className="flex items-center gap-4 p-4">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${c.bg}`}>
          <span className={c.icon}>{icon}</span>
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-body font-medium text-white text-sm">{label}</p>
          <p className="text-slate-500 text-xs">{description}</p>
        </div>
      </div>
      <div className="flex border-t border-white border-opacity-5">
        <button
          onClick={onPreview}
          className="flex-1 flex items-center justify-center gap-2 py-2.5 text-xs text-slate-400 hover:text-white hover:bg-white hover:bg-opacity-5 transition-all"
        >
          <Play size={12} /> Preview
        </button>
        <div className="w-px bg-white bg-opacity-5" />
        <a
          href={downloadUrl}
          download={filename}
          className="flex-1 flex items-center justify-center gap-2 py-2.5 text-xs text-slate-400 hover:text-white hover:bg-white hover:bg-opacity-5 transition-all"
        >
          <Download size={12} /> Download
        </a>
      </div>
    </div>
  );
}

function formatDuration(sec) {
  if (!sec) return "—";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function formatSRTTime(seconds) {
  const totalMs = Math.round(seconds * 1000);
  const ms = totalMs % 1000;
  const totalS = Math.floor(totalMs / 1000);
  const s = totalS % 60;
  const m = Math.floor(totalS / 60) % 60;
  const h = Math.floor(totalS / 3600);
  return `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")},${String(ms).padStart(3,"0")}`;
}
