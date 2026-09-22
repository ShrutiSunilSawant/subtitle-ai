import React from "react";
import { Link } from "react-router-dom";
import { Film, ArrowRight } from "lucide-react";

export default function HomePage() {
  return (
    <div className="relative">
      {/* ── Hero Section ── */}
      <section className="relative pt-24 pb-32 px-6 text-center overflow-hidden">
        {/* Grid background */}
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: "linear-gradient(rgba(34,89,245,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(34,89,245,0.3) 1px, transparent 1px)",
            backgroundSize: "60px 60px",
          }}
        />

        <div className="relative max-w-5xl mx-auto stagger-children">
          {/* Headline */}
          <h1 className="font-display font-extrabold text-6xl md:text-7xl leading-none tracking-tight text-white mb-6">
            AI Subtitles That
            <br />
            <span
              className="text-transparent bg-clip-text"
              style={{ backgroundImage: "linear-gradient(135deg, #4a7dff, #00d4ff)" }}
            >
              Understand Your Film
            </span>
          </h1>

          {/* Subheadline */}
          <p className="text-lg text-slate-400 max-w-2xl mx-auto mb-12 font-body leading-relaxed">
            Automatic speech subtitles via <strong className="text-slate-300">Whisper</strong>,
            plus AI-generated scene explainers for every silent moment,
            using <strong className="text-slate-300">BLIP</strong> computer vision.
            Built for movies, OTT content, and accessibility.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/upload" className="btn-primary flex items-center justify-center gap-2 text-base px-8 py-4">
              <Film size={18} />
              Upload Your Video
              <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
