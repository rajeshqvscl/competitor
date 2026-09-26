"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Building2, Globe2, TrendingUp, Search } from "lucide-react";
import { getCompanies } from "@/lib/api";
import { PageHeader, EmptyState, SkeletonBlock } from "@/components/ui";

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [ownershipFilter, setOwnershipFilter] = useState("");

  useEffect(() => {
    setLoading(true);
    const t = setTimeout(() => {
      const params: Record<string, string> = {};
      if (search) params.search = search;
      if (ownershipFilter) params.ownership_type = ownershipFilter;
      getCompanies(params)
        .then(setCompanies)
        .catch(console.error)
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(t);
  }, [search, ownershipFilter]);

  return (
    <div className="max-w-7xl animate-fade-in">
      <PageHeader
        title="Companies"
        subtitle="Dairy companies tracked in the intelligence platform"
      />

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search companies…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input w-full pl-9"
          />
        </div>
        <select
          value={ownershipFilter}
          onChange={(e) => setOwnershipFilter(e.target.value)}
          className="input"
        >
          <option value="">All ownership types</option>
          <option value="cooperative">Cooperative</option>
          <option value="listed">Listed</option>
          <option value="unlisted">Unlisted</option>
          <option value="global">Global</option>
        </select>
      </div>

      {/* Count */}
      {!loading && (
        <div className="text-xs text-slate-400 mb-3">
          {companies.length} {companies.length === 1 ? "company" : "companies"}
        </div>
      )}

      {loading ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonBlock key={i} className="h-24 rounded-xl" />
          ))}
        </div>
      ) : companies.length === 0 ? (
        <EmptyState
          icon={<Building2 className="w-5 h-5" />}
          title="No companies match your filters"
          subtitle="Try a different search term or ownership type"
        />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {companies.map((c) => (
            <Link
              key={c.id}
              href={`/companies/${c.id}`}
              className="card card-hover p-5 group"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-brand-50 text-brand-700 ring-1 ring-brand-100 flex items-center justify-center text-sm font-bold uppercase shrink-0">
                    {c.name.slice(0, 2)}
                  </div>
                  <div className="min-w-0">
                    <div className="font-semibold text-slate-900 truncate group-hover:text-brand-700 transition-colors">
                      {c.name}
                    </div>
                    <div className="text-xs text-slate-400 mt-0.5">
                      {c.headquarters_region?.name || "—"}
                    </div>
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-1.5 mt-4">
                {c.ownership_type && (
                  <span className="badge badge-blue capitalize">{c.ownership_type.name}</span>
                )}
                {c.is_listed && (
                  <span className="badge badge-green">
                    <TrendingUp className="w-3 h-3" /> Listed
                  </span>
                )}
                {c.is_global && (
                  <span className="badge badge-purple">
                    <Globe2 className="w-3 h-3" /> Global
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
