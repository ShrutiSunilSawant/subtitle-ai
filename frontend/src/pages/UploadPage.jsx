import React, { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useNavigate } from "react-router-dom";
import { Upload, Film, CheckCircle, AlertCircle, Globe } from "lucide-react";
import { uploadVideo, startProcessing } from "../utils/api";

const ACCEPTED = { "video/*": [".mp4", ".mov", ".mkv", ".avi", ".webm"] };
const MAX_SIZE  = 500 * 1024 * 1024;

const LANGUAGES = [
  { value: "",    label: "Auto-Detect" },
  { value: "en",  label: "English" },
  { value: "hi",  label: "Hindi" },
  { value: "ur",  label: "Urdu" },
  { value: "fr",  label: "French" },
  { value: "es",  label: "Spanish" },
  { value: "de",  label: "German" },
  { value: "ar",  label: "Arabic" },
  { value: "zh",  label: "Chinese" },
  { value: "ja",  label: "Japanese" },
  { value: "pt",  label: "Portuguese" },
  { value: "ru",  label: "Russian" },
  { value: "ko",  label: "Korean" },
  { value: "it",  label: "Italian" },
  { value: "tr",  label: "Turkish" },
];

export default function UploadPage() {
  const navigate = useNavigate();
  const [file,     setFile]     = useState(null);
  const [progress, setProgress] = useState(0);
  const [phase,    setPhase]    = useState("idle");
  const [error,    setError]    = useState("");
  const [language, setLanguage] = useState("");

  const onDrop = useCallback((accepted, rejected) => {
    if (rejected.length > 0) {
      setError(`File rejected: ${rejected[0].errors[0]?.message}`);
      return;
    }
    if (accepted.length > 0) { setFile(accepted[0]); setError(""); }
  }, []);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop, accept: ACCEPTED, maxSize: MAX_SIZE, maxFiles: 1,
  });

  const handleSubmit = async () => {
    if (!file) return;
    try {
      setError("");
      setPhase("uploading");
      const { job_id } = await uploadVideo(file, setProgress);
      setPhase("starting");
      // Smart defaults — no need to expose to user
      await startProcessing({
        job_id,
        language:                language || null,
        silence_threshold_db:    -35,      // balanced sensitivity
        min_silence_duration_sec: 5.0,     // 5s non-speech gaps for scene captions
        burn_subtitles:          true,
      });
      navigate(`/processing/${job_id}`);
    } catch (err) {
      setPhase("error");
      setError(err.response?.data?.detail || err.message || "Unexpected error.");
    }
  };

  const isLoading = phase === "uploading" || phase === "starting";
  const fmt = (b) => b < 1048576 ? `${(b/1024).toFixed(1)} KB` : `${(b/1048576).toFixed(1)} MB`;

  return (
    <div className="max-w-2xl mx-auto px-6 py-20 animate-fade-in-up">

      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="font-display font-bold text-4xl text-white mb-3">
          Upload Your Video
        </h1>
        <p className="text-slate-400 text-sm">
          MP4 · MOV · MKV · AVI · WebM &nbsp;·&nbsp; Up to 500 MB
        </p>
      </div>

      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-2xl p-16 text-center cursor-pointer
          transition-all duration-300 mb-6
          ${isDragReject  ? "border-accent-rose bg-rose-950 bg-opacity-20" :
            isDragActive  ? "border-brand-400 bg-brand-950 bg-opacity-20 shadow-glow-brand" :
            file          ? "border-accent-emerald bg-emerald-950 bg-opacity-10" :
            "border-surface-600 hover:border-brand-500 hover:bg-surface-800 hover:bg-opacity-30"}
        `}
      >
        <input {...getInputProps()} />

        {file ? (
          <div className="flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-emerald-900 bg-opacity-40 flex items-center justify-center">
              <CheckCircle size={26} className="text-accent-emerald" />
            </div>
            <p className="font-display font-semibold text-white text-lg">{file.name}</p>
            <p className="text-slate-500 text-sm">{fmt(file.size)}</p>
            <button
              onClick={(e) => { e.stopPropagation(); setFile(null); setProgress(0); setPhase("idle"); }}
              className="text-xs text-slate-600 hover:text-accent-rose transition-colors mt-1"
            >
              Remove
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4">
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-300 ${isDragActive ? "bg-brand-600 shadow-glow-brand" : "bg-surface-700"}`}>
              <Upload size={28} className={isDragActive ? "text-white" : "text-slate-400"} />
            </div>
            <div>
              <p className="font-display font-semibold text-white text-lg">
                {isDragActive ? "Drop it here!" : "Drag & drop your video"}
              </p>
              <p className="text-slate-500 text-sm mt-1">
                or <span className="text-brand-400 cursor-pointer">browse files</span>
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Upload Progress */}
      {phase === "uploading" && (
        <div className="mb-5">
          <div className="flex justify-between text-xs text-slate-500 mb-2">
            <span>Uploading…</span><span>{progress}%</span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-start gap-3 p-4 rounded-xl bg-rose-950 bg-opacity-40 border border-accent-rose border-opacity-30 mb-5">
          <AlertCircle size={16} className="text-accent-rose flex-shrink-0 mt-0.5" />
          <p className="text-rose-300 text-sm">{error}</p>
        </div>
      )}

      {/* Subtitle Language — only setting user needs */}
      <div className="glass-card p-5 mb-6">
        <div className="flex items-center gap-2 mb-3">
          <Globe size={15} className="text-brand-400" />
          <label className="text-white font-semibold text-sm">Subtitle Language</label>
          <span className="ml-auto text-xs text-slate-500">Optional</span>
        </div>
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="w-full bg-surface-700 border border-white border-opacity-10 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-brand-500 transition-colors"
        >
          {LANGUAGES.map(l => (
            <option key={l.value} value={l.value}>{l.label}</option>
          ))}
        </select>
        <p className="text-slate-600 text-xs mt-2">
          Leave as Auto-Detect for most videos. Set manually for better accuracy.
        </p>
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!file || isLoading}
        className={`
          w-full flex items-center justify-center gap-3 py-4 rounded-2xl
          font-display font-semibold text-lg transition-all duration-300
          ${!file || isLoading
            ? "bg-surface-700 text-slate-600 cursor-not-allowed"
            : "btn-primary"}
        `}
      >
        <Film size={20} />
        {phase === "starting"  ? "Starting…"         :
         phase === "uploading" ? `Uploading ${progress}%` :
         "Generate Subtitles"}
      </button>

      {/* What happens next */}
      {!file && (
        <div className="mt-8 grid grid-cols-3 gap-4 text-center">
          {[
            { icon: "🎙️", label: "Speech transcribed" },
            { icon: "🎬", label: "Scenes described"   },
            { icon: "📥", label: "Download ready"     },
          ].map((item, i) => (
            <div key={i} className="glass-card p-4">
              <div className="text-2xl mb-2">{item.icon}</div>
              <p className="text-slate-500 text-xs">{item.label}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
