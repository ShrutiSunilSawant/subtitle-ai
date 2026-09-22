import React from "react";
import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import HomePage from "./pages/HomePage";
import UploadPage from "./pages/UploadPage";
import ProcessingPage from "./pages/ProcessingPage";
import ResultsPage from "./pages/ResultsPage";

export default function App() {
  return (
    <div className="relative min-h-screen bg-surface-950 font-body overflow-x-hidden">
      {/* Ambient background glows */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-brand-600 opacity-5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-accent-cyan opacity-5 rounded-full blur-3xl" />
      </div>

      {/* Navbar */}
      <Navbar />

      {/* Page routes */}
      <main className="relative z-10">
        <Routes>
          <Route path="/"              element={<HomePage />} />
          <Route path="/upload"        element={<UploadPage />} />
          <Route path="/processing/:jobId" element={<ProcessingPage />} />
          <Route path="/results/:jobId"    element={<ResultsPage />} />
        </Routes>
      </main>
    </div>
  );
}
