import React from "react";
import { Link, useLocation } from "react-router-dom";
import { Film, Zap } from "lucide-react";

export default function Navbar() {
  const { pathname } = useLocation();

  return (
    <nav className="sticky top-0 z-50 border-b border-white border-opacity-5 backdrop-blur-md bg-surface-950 bg-opacity-80">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center group-hover:shadow-glow-brand transition-all duration-300">
            <Film size={18} className="text-white" />
          </div>
          <span className="font-display font-bold text-xl text-white tracking-tight">
            Subtitle<span className="text-brand-400">AI</span>
          </span>
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-8">
          <NavLink to="/" label="Home" active={pathname === "/"} />
          <NavLink to="/upload" label="Upload" active={pathname === "/upload"} />
        </div>

        {/* CTA */}
        <Link
          to="/upload"
          className="flex items-center gap-2 btn-primary text-sm"
        >
          <Zap size={15} />
          Get Started
        </Link>
      </div>
    </nav>
  );
}

function NavLink({ to, label, active }) {
  return (
    <Link
      to={to}
      className={`text-sm font-body font-medium transition-colors duration-200 ${
        active ? "text-brand-400" : "text-slate-400 hover:text-white"
      }`}
    >
      {label}
    </Link>
  );
}
