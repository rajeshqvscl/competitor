"use client";

import { useState } from "react";
import { exportCsv } from "@/lib/api";

interface ExportButtonProps {
  endpoint: string;
  data: any;
  filename: string;
  label?: string;
}

export default function ExportButton({ endpoint, data, filename, label }: ExportButtonProps) {
  const [loading, setLoading] = useState(false);

  const handleExport = async () => {
    setLoading(true);
    try {
      await exportCsv(endpoint, data, filename);
    } catch (e) {
      console.error("Export failed:", e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleExport}
      disabled={loading}
      className="btn-secondary text-sm flex items-center gap-2"
    >
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      {loading ? "Exporting..." : (label || "Export CSV")}
    </button>
  );
}
