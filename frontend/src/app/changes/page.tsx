"use client";

import { useEffect, useState } from "react";
import { getChanges } from "@/lib/api";

const EVENT_TYPES = [
  { value: "", label: "All Events" },
  { value: "SKU_ADDED", label: "SKU Added" },
  { value: "SKU_REMOVED", label: "SKU Removed" },
  { value: "PRICE_CHANGED", label: "Price Changed" },
  { value: "RETAILER_ADDED", label: "Retailer Added" },
  { value: "RETAILER_REMOVED", label: "Retailer Removed" },
  { value: "REGION_ADDED", label: "Region Added" },
  { value: "COMPANY_UPDATED", label: "Company Updated" },
];

const EVENT_ICONS: Record<string, string> = {
  SKU_ADDED: "&#10010;",
  SKU_REMOVED: "&#10060;",
  PRICE_CHANGED: "&#128176;",
  RETAILER_ADDED: "&#127970;",
  RETAILER_REMOVED: "&#128680;",
  REGION_ADDED: "&#127758;",
  COMPANY_UPDATED: "&#128221;",
};

const EVENT_COLORS: Record<string, string> = {
  SKU_ADDED: "badge-green",
  SKU_REMOVED: "badge-yellow",
  PRICE_CHANGED: "badge-blue",
  RETAILER_ADDED: "badge-green",
  RETAILER_REMOVED: "badge-yellow",
  REGION_ADDED: "badge-purple",
  COMPANY_UPDATED: "badge-blue",
};

export default function ChangesPage() {
  const [changes, setChanges] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [eventTypeFilter, setEventTypeFilter] = useState("");
  const [entityTypeFilter, setEntityTypeFilter] = useState("");

  useEffect(() => {
    const params: Record<string, string> = {};
    if (eventTypeFilter) params.event_type = eventTypeFilter;
    if (entityTypeFilter) params.entity_type = entityTypeFilter;
    getChanges(params)
      .then((res) => setChanges(res.changes || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [eventTypeFilter, entityTypeFilter]);

  const formatDate = (iso: string) => {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Change Detection</h1>
      <p className="text-gray-500 mb-6">Track SKU additions, removals, price changes, and other market events</p>

      <div className="flex gap-4 mb-6">
        <select
          value={eventTypeFilter}
          onChange={(e) => setEventTypeFilter(e.target.value)}
          className="input"
        >
          {EVENT_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
        <select
          value={entityTypeFilter}
          onChange={(e) => setEntityTypeFilter(e.target.value)}
          className="input"
        >
          <option value="">All Entities</option>
          <option value="sku">SKUs</option>
          <option value="company">Companies</option>
          <option value="retailer">Retailers</option>
        </select>
      </div>

      {loading ? (
        <div className="text-gray-500">Loading...</div>
      ) : changes.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-4xl mb-4">&#128337;</div>
          <div className="text-lg text-gray-500 mb-2">No changes detected yet</div>
          <div className="text-sm text-gray-400">Changes will appear here when data is updated</div>
        </div>
      ) : (
        <div className="grid gap-3">
          {changes.map((c) => (
            <div key={c.id} className="card p-4">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <span
                    className="text-lg"
                    dangerouslySetInnerHTML={{ __html: EVENT_ICONS[c.event_type] || "&#128196;" }}
                  />
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`badge ${EVENT_COLORS[c.event_type] || "badge-blue"}`}>
                        {c.event_type.replace(/_/g, " ")}
                      </span>
                      <span className="text-xs text-gray-400">{c.entity_type} #{c.entity_id}</span>
                    </div>
                    <div className="text-sm text-gray-700">
                      {c.description || `${c.field_name}: ${c.old_value} → ${c.new_value}`}
                    </div>
                    {c.old_value && c.new_value && (
                      <div className="text-xs text-gray-500 mt-1">
                        <span className="line-through">{c.old_value}</span>
                        {" → "}
                        <span className="font-medium text-green-600">{c.new_value}</span>
                      </div>
                    )}
                  </div>
                </div>
                <div className="text-xs text-gray-400 whitespace-nowrap">
                  {formatDate(c.detected_at)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
