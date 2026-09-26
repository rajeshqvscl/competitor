"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Building2, Milk, Package, Boxes, Store, MapPin,
  SearchCheck, LayoutGrid, BarChart3, Truck, ArrowRight,
} from "lucide-react";
import { getDashboardStats, getCompanies } from "@/lib/api";
import { PageHeader, StatCard, ProgressRow, SkeletonBlock } from "@/components/ui";

const BAR_COLORS: Record<string, string> = {
  cooperative: "bg-sky-500",
  listed: "bg-emerald-500",
  unlisted: "bg-amber-500",
  global: "bg-violet-500",
};

const ACTION_ICONS: Record<string, React.ReactNode> = {
  search: <SearchCheck className="w-5 h-5" />,
  grid: <LayoutGrid className="w-5 h-5" />,
  chart: <BarChart3 className="w-5 h-5" />,
  truck: <Truck className="w-5 h-5" />,
};

const QUICK_ACTIONS = [
  { href: "/analysis", label: "Competitor Analysis", desc: "Overlap & positioning", icon: "search" },
  { href: "/companies", label: "Browse Companies", desc: "15+ players tracked", icon: "grid" },
  { href: "/compare", label: "Compare Portfolios", desc: "Side-by-side SKUs", icon: "chart" },
  { href: "/distributors", label: "Distribution Map", desc: "Network coverage", icon: "truck" },
];

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null);
  const [topCompanies, setTopCompanies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getDashboardStats(), getCompanies({ limit: "6" })])
      .then(([s, c]) => {
        setStats(s);
        setTopCompanies(c);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const ownership = (stats?.companies_by_ownership || {}) as Record<string, number>;
  const ownershipMax = Math.max(1, ...Object.values(ownership).map(Number));
  const regions = (stats?.companies_by_region || {}) as Record<string, number>;
  const regionMax = Math.max(1, ...Object.values(regions).map(Number));
  const skusByCat = (stats?.skus_by_category || {}) as Record<string, number>;
  const skuMax = Math.max(1, ...Object.values(skusByCat).map(Number));

  return (
    <div className="max-w-7xl animate-fade-in">
      <PageHeader
        title="Dashboard"
        subtitle="Snapshot of the Indian dairy competitive landscape"
      />

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
        <StatCard loading={loading} label="Companies" value={stats?.total_companies} color="blue" icon={<Building2 className="w-4 h-4" />} />
        <StatCard loading={loading} label="Brands" value={stats?.total_brands} color="green" icon={<Milk className="w-4 h-4" />} />
        <StatCard loading={loading} label="Products" value={stats?.total_products} color="purple" icon={<Package className="w-4 h-4" />} />
        <StatCard loading={loading} label="SKUs" value={stats?.total_skus} color="yellow" icon={<Boxes className="w-4 h-4" />} />
        <StatCard loading={loading} label="Retailers" value={stats?.total_retailers} color="pink" icon={<Store className="w-4 h-4" />} />
        <StatCard loading={loading} label="Regions" value={stats?.total_regions} color="indigo" icon={<MapPin className="w-4 h-4" />} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Ownership breakdown */}
        <div className="card p-5">
          <h2 className="font-semibold text-slate-800 mb-4">Companies by Ownership</h2>
          <div className="space-y-4">
            {loading
              ? Array.from({ length: 4 }).map((_, i) => <SkeletonBlock key={i} className="h-9" />)
              : Object.entries(ownership).map(([key, val]) => (
                  <ProgressRow
                    key={key}
                    label={key.charAt(0).toUpperCase() + key.slice(1)}
                    count={Number(val)}
                    pct={(Number(val) / ownershipMax) * 100}
                    barClass={BAR_COLORS[key] || "bg-slate-400"}
                  />
                ))}
            {!loading && Object.keys(ownership).length === 0 && (
              <div className="text-sm text-slate-400">No data</div>
            )}
          </div>
        </div>

        {/* Region breakdown */}
        <div className="card p-5">
          <h2 className="font-semibold text-slate-800 mb-4">Companies by Region</h2>
          <div className="space-y-4">
            {loading
              ? Array.from({ length: 5 }).map((_, i) => <SkeletonBlock key={i} className="h-9" />)
              : Object.entries(regions)
                  .sort(([, a], [, b]) => (b as number) - (a as number))
                  .slice(0, 8)
                  .map(([key, val]) => (
                    <ProgressRow
                      key={key}
                      label={key}
                      count={Number(val)}
                      pct={(Number(val) / regionMax) * 100}
                      barClass="bg-brand-500"
                    />
                  ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* SKUs by category */}
        <div className="card p-5">
          <h2 className="font-semibold text-slate-800 mb-4">SKUs by Category</h2>
          <div className="space-y-4">
            {loading
              ? Array.from({ length: 5 }).map((_, i) => <SkeletonBlock key={i} className="h-9" />)
              : Object.entries(skusByCat)
                  .sort(([, a], [, b]) => (b as number) - (a as number))
                  .map(([key, val]) => (
                    <ProgressRow
                      key={key}
                      label={key}
                      count={Number(val)}
                      pct={(Number(val) / skuMax) * 100}
                      barClass="bg-violet-500"
                    />
                  ))}
          </div>
        </div>

        {/* Top companies */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-slate-800">Tracked Companies</h2>
            <Link href="/companies" className="text-sm text-brand-600 hover:text-brand-700 font-medium inline-flex items-center gap-1">
              View all <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          <div className="space-y-1">
            {loading
              ? Array.from({ length: 5 }).map((_, i) => <SkeletonBlock key={i} className="h-11" />)
              : topCompanies.map((c) => (
                  <Link
                    key={c.id}
                    href={`/companies/${c.id}`}
                    className="flex items-center justify-between py-2.5 px-3 -mx-1 rounded-lg hover:bg-slate-50 transition-colors group"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-brand-50 text-brand-700 ring-1 ring-brand-100 flex items-center justify-center text-xs font-bold uppercase">
                        {c.name.slice(0, 2)}
                      </div>
                      <div>
                        <div className="text-sm font-medium text-slate-800 group-hover:text-brand-700 transition-colors">{c.name}</div>
                        <div className="text-xs text-slate-400">{c.headquarters_region?.name || "—"}</div>
                      </div>
                    </div>
                    {c.ownership_type && (
                      <span className="badge badge-blue capitalize">{c.ownership_type.name}</span>
                    )}
                  </Link>
                ))}
          </div>
        </div>
      </div>

      {/* Quick actions */}
      <div className="card p-5">
        <h2 className="font-semibold text-slate-800 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {QUICK_ACTIONS.map(({ href, label, desc, icon }) => (
            <Link
              key={href}
              href={href}
              className="card card-hover p-4 text-left"
            >
              <div className="w-9 h-9 rounded-lg bg-brand-50 text-brand-600 ring-1 ring-brand-100 flex items-center justify-center mb-3">
                {ACTION_ICONS[icon]}
              </div>
              <div className="text-sm font-semibold text-slate-800">{label}</div>
              <div className="text-xs text-slate-400 mt-0.5">{desc}</div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
