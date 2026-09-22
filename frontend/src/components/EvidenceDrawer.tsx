"use client";

import { useEffect, useState } from "react";
import { getEntitySources } from "@/lib/api";

interface EvidenceDrawerProps {
  entityType: string;
  entityId: number;
  label?: string;
  children?: React.ReactNode;
}

export default function EvidenceDrawer({ entityType, entityId, label, children }: EvidenceDrawerProps) {
  const [open, setOpen] = useState(false);
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open && sources.length === 0) {
      setLoading(true);
      getEntitySources(entityType, entityId)
        .then((res) => setSources(res.sources || []))
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [open, entityType, entityId]);

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="text-blue-600 hover:text-blue-800 text-xs underline transition-colors"
      >
        {label || "View Source"}
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/30" onClick={() => setOpen(false)} />
          <div className="relative w-96 bg-white shadow-xl overflow-auto">
            <div className="sticky top-0 bg-white border-b px-4 py-3 flex items-center justify-between z-10">
              <h3 className="font-semibold text-sm">Evidence & Sources</h3>
              <button
                onClick={() => setOpen(false)}
                className="text-gray-400 hover:text-gray-600 text-lg"
              >
                &times;
              </button>
            </div>

            <div className="p-4">
              <div className="text-xs text-gray-500 mb-3">
                {entityType} #{entityId} — {sources.length} source{sources.length !== 1 ? "s" : ""}
              </div>

              {loading && <div className="text-gray-400 text-sm">Loading sources...</div>}

              {!loading && sources.length === 0 && (
                <div className="text-gray-400 text-sm">No sources recorded for this item.</div>
              )}

              <div className="space-y-3">
                {sources.map((src) => (
                  <div key={src.id} className="border rounded-lg p-3 text-sm">
                    <div className="flex items-center justify-between mb-2">
                      <span className={`badge ${
                        src.confidence === "high" ? "badge-green" :
                        src.confidence === "medium" ? "badge-yellow" : "badge-purple"
                      }`}>
                        {src.confidence || "unknown"}
                      </span>
                      <span className="text-xs text-gray-400">
                        {src.source_type?.replace("_", " ") || "unknown"}
                      </span>
                    </div>

                    {src.extracted_fact && (
                      <div className="text-gray-700 mb-2">{src.extracted_fact}</div>
                    )}

                    {src.source_url && (
                      <a
                        href={src.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline text-xs break-all"
                      >
                        {src.source_url}
                      </a>
                    )}

                    <div className="flex gap-3 mt-2 text-xs text-gray-400">
                      {src.extraction_date && <span>Extracted: {src.extraction_date}</span>}
                      {src.last_verified && <span>Verified: {src.last_verified}</span>}
                    </div>
                  </div>
                ))}
              </div>

              {children}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
