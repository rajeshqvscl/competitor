"use client";

import { useEffect, useState } from "react";
import { getAlerts, createAlert, deleteAlert, markAlertRead, getCompanies, getCategories } from "@/lib/api";

const EVENT_TYPES = [
  { value: "SKU_ADDED", label: "New SKU" },
  { value: "SKU_REMOVED", label: "SKU Discontinued" },
  { value: "PRICE_CHANGED", label: "Price Change" },
  { value: "RETAILER_ADDED", label: "New Retailer" },
  { value: "RETAILER_REMOVED", label: "Retailer Removed" },
  { value: "REGION_ADDED", label: "New Region" },
];

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [companies, setCompanies] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newAlert, setNewAlert] = useState({
    name: "",
    company_id: 0,
    category_id: 0,
    event_types: [] as string[],
  });

  useEffect(() => {
    Promise.all([
      getAlerts(),
      getCompanies(),
      getCategories(),
    ])
      .then(([a, c, cat]) => {
        setAlerts(a);
        setCompanies(c);
        setCategories(cat);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleCreate = async () => {
    if (!newAlert.name.trim()) return;
    try {
      await createAlert({
        name: newAlert.name,
        company_id: newAlert.company_id || undefined,
        category_id: newAlert.category_id || undefined,
        event_types: newAlert.event_types,
      });
      const updated = await getAlerts();
      setAlerts(updated);
      setShowCreate(false);
      setNewAlert({ name: "", company_id: 0, category_id: 0, event_types: [] });
    } catch (e) {
      console.error(e);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this alert?")) return;
    try {
      await deleteAlert(id);
      setAlerts((prev) => prev.filter((a) => a.id !== id));
    } catch (e) {
      console.error(e);
    }
  };

  const handleMarkRead = async (id: number) => {
    try {
      await markAlertRead(id);
      setAlerts((prev) =>
        prev.map((a) => (a.id === id ? { ...a, unread_count: 0 } : a))
      );
    } catch (e) {
      console.error(e);
    }
  };

  const toggleEventType = (et: string) => {
    setNewAlert((prev) => ({
      ...prev,
      event_types: prev.event_types.includes(et)
        ? prev.event_types.filter((e) => e !== et)
        : [...prev.event_types, et],
    }));
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Alerts</h1>
          <p className="text-gray-500 text-sm">Subscribe to competitor changes and get notified</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary">
          + New Alert
        </button>
      </div>

      {loading ? (
        <div className="text-gray-500">Loading...</div>
      ) : alerts.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-4xl mb-4">&#128276;</div>
          <div className="text-lg text-gray-500 mb-2">No alerts yet</div>
          <div className="text-sm text-gray-400 mb-4">Create an alert to track competitor changes</div>
          <button onClick={() => setShowCreate(true)} className="btn-primary">
            Create Your First Alert
          </button>
        </div>
      ) : (
        <div className="grid gap-3">
          {alerts.map((alert) => (
            <div key={alert.id} className={`card p-4 ${alert.unread_count > 0 ? "ring-2 ring-blue-200 bg-blue-50" : ""}`}>
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{alert.name}</span>
                    {alert.unread_count > 0 && (
                      <span className="badge bg-red-100 text-red-800">{alert.unread_count} new</span>
                    )}
                    {!alert.is_active && (
                      <span className="badge bg-gray-100 text-gray-500">Paused</span>
                    )}
                  </div>
                  <div className="text-sm text-gray-500 mt-1">
                    {alert.company_name && <span>Company: {alert.company_name}</span>}
                    {alert.category_name && <span> | Category: {alert.category_name}</span>}
                    {alert.region_name && <span> | Region: {alert.region_name}</span>}
                  </div>
                  <div className="flex gap-1 mt-2">
                    {alert.event_types?.map((et: string) => (
                      <span key={et} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                        {et.replace(/_/g, " ")}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2">
                  {alert.unread_count > 0 && (
                    <button onClick={() => handleMarkRead(alert.id)} className="btn-secondary text-xs">
                      Mark Read
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(alert.id)}
                    className="text-gray-400 hover:text-red-500 text-sm"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Dialog */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/30" onClick={() => setShowCreate(false)} />
          <div className="relative bg-white rounded-xl shadow-xl p-6 w-[500px]">
            <h3 className="text-lg font-semibold mb-4">Create Alert</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Alert Name *</label>
                <input
                  type="text"
                  value={newAlert.name}
                  onChange={(e) => setNewAlert({ ...newAlert, name: e.target.value })}
                  placeholder="e.g. Amul Price Changes"
                  className="input w-full"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Company (optional)</label>
                  <select
                    value={newAlert.company_id}
                    onChange={(e) => setNewAlert({ ...newAlert, company_id: Number(e.target.value) })}
                    className="input w-full"
                  >
                    <option value={0}>All companies</option>
                    {companies.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category (optional)</label>
                  <select
                    value={newAlert.category_id}
                    onChange={(e) => setNewAlert({ ...newAlert, category_id: Number(e.target.value) })}
                    className="input w-full"
                  >
                    <option value={0}>All categories</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Event Types</label>
                <div className="flex flex-wrap gap-2">
                  {EVENT_TYPES.map((et) => (
                    <button
                      key={et.value}
                      onClick={() => toggleEventType(et.value)}
                      className={`text-sm px-3 py-1 rounded-full border transition-colors ${
                        newAlert.event_types.includes(et.value)
                          ? "bg-blue-600 text-white border-blue-600"
                          : "bg-white text-gray-700 border-gray-300"
                      }`}
                    >
                      {et.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button onClick={() => setShowCreate(false)} className="btn-secondary">Cancel</button>
                <button onClick={handleCreate} disabled={!newAlert.name.trim()} className="btn-primary disabled:opacity-50">
                  Create Alert
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
