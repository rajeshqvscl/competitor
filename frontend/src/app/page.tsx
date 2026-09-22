"use client";

import { useEffect, useState } from "react";
import { getDashboardStats, getCompanies } from "@/lib/api";

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null);
  const [topCompanies, setTopCompanies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getDashboardStats(),
      getCompanies({ limit: "10" }),
    ])
      .then(([s, c]) => {
        setStats(s);
        setTopCompanies(c);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-gray-500">Loading...</div>;
  if (!stats) return <div className="text-red-500">Failed to load stats</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
        <StatCard label="Companies" value={stats.total_companies} color="blue" />
        <StatCard label="Brands" value={stats.total_brands} color="green" />
        <StatCard label="Products" value={stats.total_products} color="purple" />
        <StatCard label="SKUs" value={stats.total_skus} color="yellow" />
        <StatCard label="Retailers" value={stats.total_retailers} color="pink" />
        <StatCard label="Regions" value={stats.total_regions} color="indigo" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Ownership breakdown */}
        <div className="card p-4">
          <h2 className="font-semibold mb-4">Companies by Ownership</h2>
          <div className="space-y-3">
            {Object.entries(stats.companies_by_ownership || {}).map(([key, val]) => {
              const count = val as number;
              const pct = stats.total_companies > 0 ? Math.round((count / stats.total_companies) * 100) : 0;
              return (
                <div key={key}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="capitalize font-medium">{key}</span>
                    <span className="text-gray-500">{count} ({pct}%)</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        key === "cooperative" ? "bg-blue-500" :
                        key === "listed" ? "bg-green-500" :
                        key === "unlisted" ? "bg-yellow-500" : "bg-purple-500"
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Region breakdown */}
        <div className="card p-4">
          <h2 className="font-semibold mb-4">Companies by Region</h2>
          <div className="space-y-3">
            {Object.entries(stats.companies_by_region || {})
              .sort(([, a], [, b]) => (b as number) - (a as number))
              .slice(0, 8)
              .map(([key, val]) => {
                const count = val as number;
                const maxCount = Math.max(...Object.values(stats.companies_by_region).map(Number));
                const pct = maxCount > 0 ? Math.round((count / maxCount) * 100) : 0;
                return (
                  <div key={key}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-medium">{key}</span>
                      <span className="text-gray-500">{count}</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div className="h-2 rounded-full bg-blue-500" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* SKUs by category */}
        <div className="card p-4">
          <h2 className="font-semibold mb-4">SKUs by Category</h2>
          <div className="space-y-3">
            {Object.entries(stats.skus_by_category || {})
              .sort(([, a], [, b]) => (b as number) - (a as number))
              .map(([key, val]) => {
                const count = val as number;
                const maxCount = Math.max(...Object.values(stats.skus_by_category).map(Number));
                const pct = maxCount > 0 ? Math.round((count / maxCount) * 100) : 0;
                return (
                  <div key={key}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-medium">{key}</span>
                      <span className="text-gray-500">{count}</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div className="h-2 rounded-full bg-purple-500" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
          </div>
        </div>

        {/* Top companies */}
        <div className="card p-4">
          <h2 className="font-semibold mb-4">Companies</h2>
          <div className="space-y-2">
            {topCompanies.slice(0, 10).map((c) => (
              <a
                key={c.id}
                href={`/companies/${c.id}`}
                className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div>
                  <span className="font-medium text-sm">{c.name}</span>
                  <span className="text-xs text-gray-400 ml-2">{c.headquarters_region?.name}</span>
                </div>
                <div className="flex gap-1">
                  {c.ownership_type && (
                    <span className="badge badge-blue text-xs">{c.ownership_type.name}</span>
                  )}
                </div>
              </a>
            ))}
          </div>
        </div>
      </div>

      {/* Quick actions */}
      <div className="card p-4">
        <h2 className="font-semibold mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <a href="/analysis" className="card p-3 text-center hover:shadow-md transition-shadow">
            <div className="text-2xl mb-1">&#128269;</div>
            <div className="text-sm font-medium">Competitor Analysis</div>
          </a>
          <a href="/companies" className="card p-3 text-center hover:shadow-md transition-shadow">
            <div className="text-2xl mb-1">&#127970;</div>
            <div className="text-sm font-medium">Browse Companies</div>
          </a>
          <a href="/categories" className="card p-3 text-center hover:shadow-md transition-shadow">
            <div className="text-2xl mb-1">&#128193;</div>
            <div className="text-sm font-medium">Category Explorer</div>
          </a>
          <a href="/search" className="card p-3 text-center hover:shadow-md transition-shadow">
            <div className="text-2xl mb-1">&#128270;</div>
            <div className="text-sm font-medium">Search</div>
          </a>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  const colorMap: Record<string, string> = {
    blue: "text-blue-600",
    green: "text-green-600",
    purple: "text-purple-600",
    yellow: "text-yellow-600",
    pink: "text-pink-600",
    indigo: "text-indigo-600",
  };
  return (
    <div className="card p-4 text-center">
      <div className={`text-2xl font-bold ${colorMap[color] || "text-blue-600"}`}>{value}</div>
      <div className="text-sm text-gray-500 mt-1">{label}</div>
    </div>
  );
}
