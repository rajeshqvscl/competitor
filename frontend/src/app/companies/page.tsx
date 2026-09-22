"use client";

import { useEffect, useState } from "react";
import { getCompanies } from "@/lib/api";

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [ownershipFilter, setOwnershipFilter] = useState("");

  useEffect(() => {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    if (ownershipFilter) params.ownership_type = ownershipFilter;
    getCompanies(params)
      .then(setCompanies)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [search, ownershipFilter]);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Companies</h1>

      <div className="flex gap-4 mb-6">
        <input
          type="text"
          placeholder="Search companies..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input flex-1"
        />
        <select
          value={ownershipFilter}
          onChange={(e) => setOwnershipFilter(e.target.value)}
          className="input"
        >
          <option value="">All Types</option>
          <option value="cooperative">Cooperative</option>
          <option value="listed">Listed</option>
          <option value="unlisted">Unlisted</option>
          <option value="global">Global</option>
        </select>
      </div>

      {loading ? (
        <div className="text-gray-500">Loading...</div>
      ) : (
        <div className="grid gap-3">
          {companies.map((c) => (
            <a
              key={c.id}
              href={`/companies/${c.id}`}
              className="card p-4 hover:shadow-md transition-shadow block"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold text-lg">{c.name}</div>
                  <div className="text-sm text-gray-500">
                    {c.headquarters_region?.name || "—"}
                  </div>
                </div>
                <div className="flex gap-2">
                  {c.ownership_type && (
                    <span className="badge badge-blue capitalize">
                      {c.ownership_type.name}
                    </span>
                  )}
                  {c.is_listed && <span className="badge badge-green">Listed</span>}
                  {c.is_global && <span className="badge badge-purple">Global</span>}
                </div>
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
