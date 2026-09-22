"use client";

import { useEffect, useState } from "react";
import { getReviewQueue, approveReviewItem, rejectReviewItem } from "@/lib/api";

const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
];

export default function ReviewQueuePage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("pending");

  useEffect(() => {
    const params: Record<string, string> = {};
    if (statusFilter) params.status = statusFilter;
    getReviewQueue(params)
      .then(setItems)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [statusFilter]);

  const handleApprove = async (id: number) => {
    try {
      await approveReviewItem(id, { reviewed_by: "admin" });
      setItems((prev) => prev.map((i) => (i.id === id ? { ...i, status: "approved" } : i)));
    } catch (e) {
      console.error(e);
    }
  };

  const handleReject = async (id: number) => {
    try {
      await rejectReviewItem(id, { reviewed_by: "admin", notes: "Rejected via UI" });
      setItems((prev) => prev.map((i) => (i.id === id ? { ...i, status: "rejected" } : i)));
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

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Review Queue</h1>
      <p className="text-gray-500 mb-6">Review and approve new or updated data entries</p>

      <div className="flex gap-2 mb-6">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatusFilter(f.value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              statusFilter === f.value
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-gray-500">Loading...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-4xl mb-4">&#10003;</div>
          <div className="text-lg text-gray-500">No items to review</div>
        </div>
      ) : (
        <div className="grid gap-3">
          {items.map((item) => (
            <div key={item.id} className="card p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`badge ${
                      item.status === "pending" ? "badge-yellow" :
                      item.status === "approved" ? "badge-green" : "badge-purple"
                    }`}>
                      {item.status}
                    </span>
                    <span className="badge badge-blue">{item.action}</span>
                    <span className="text-xs text-gray-400">{item.entity_type} #{item.entity_id}</span>
                  </div>

                  {item.data && (
                    <div className="bg-gray-50 rounded-lg p-3 text-sm font-mono mb-2">
                      {typeof item.data === "object" ? (
                        <pre className="whitespace-pre-wrap">{JSON.stringify(item.data, null, 2)}</pre>
                      ) : (
                        item.data
                      )}
                    </div>
                  )}

                  {item.notes && (
                    <div className="text-sm text-gray-500">Notes: {item.notes}</div>
                  )}

                  <div className="text-xs text-gray-400 mt-2">
                    Created: {formatDate(item.created_at)}
                    {item.reviewed_by && ` | Reviewed by: ${item.reviewed_by}`}
                  </div>
                </div>

                {item.status === "pending" && (
                  <div className="flex gap-2 ml-4">
                    <button
                      onClick={() => handleApprove(item.id)}
                      className="btn-primary text-sm bg-green-600 hover:bg-green-700"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => handleReject(item.id)}
                      className="btn-secondary text-sm text-red-600 hover:bg-red-50"
                    >
                      Reject
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
