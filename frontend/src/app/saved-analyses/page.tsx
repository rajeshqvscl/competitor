"use client";

import { useEffect, useState } from "react";
import { getSavedAnalyses, deleteAnalysis } from "@/lib/api";

export default function SavedAnalysesPage() {
  const [analyses, setAnalyses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSavedAnalyses()
      .then(setAnalyses)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this saved analysis?")) return;
    try {
      await deleteAnalysis(id);
      setAnalyses((prev) => prev.filter((a) => a.id !== id));
    } catch (e) {
      console.error(e);
    }
  };

  const formatDate = (iso: string) => {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  };

  const loadAnalysis = (analysis: any) => {
    // Store filters in sessionStorage and redirect to analysis page
    if (analysis.filters) {
      sessionStorage.setItem("analysisFilters", JSON.stringify(analysis.filters));
      window.location.href = "/analysis";
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Saved Analyses</h1>
      <p className="text-gray-500 mb-6">Access your previously saved competitor analyses</p>

      {loading ? (
        <div className="text-gray-500">Loading...</div>
      ) : analyses.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-4xl mb-4">&#128190;</div>
          <div className="text-lg text-gray-500 mb-2">No saved analyses yet</div>
          <div className="text-sm text-gray-400 mb-4">
            Run an analysis and click "Save" to store it here
          </div>
          <a href="/analysis" className="btn-primary">
            Go to Analysis
          </a>
        </div>
      ) : (
        <div className="grid gap-3">
          {analyses.map((a) => (
            <div key={a.id} className="card p-4">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="font-semibold text-lg">{a.name}</div>
                  {a.description && (
                    <div className="text-sm text-gray-500 mt-1">{a.description}</div>
                  )}
                  <div className="flex gap-4 mt-2 text-xs text-gray-400">
                    <span>Created: {formatDate(a.created_at)}</span>
                    <span>Updated: {formatDate(a.updated_at)}</span>
                    {a.filters && (
                      <span>
                        Filters:{" "}
                        {Object.entries(a.filters)
                          .filter(([, v]) => v)
                          .map(([k, v]) => `${k}=${v}`)
                          .join(", ")}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => loadAnalysis(a)}
                    className="btn-primary text-sm"
                  >
                    Load
                  </button>
                  <button
                    onClick={() => handleDelete(a.id)}
                    className="btn-secondary text-sm text-red-600 hover:bg-red-50"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
