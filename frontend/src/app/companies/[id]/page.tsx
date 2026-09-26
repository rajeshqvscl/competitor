"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ChevronLeft, ExternalLink, Building2 } from "lucide-react";
import { getCompany, getCompanyBrands, getCompanySkus, getCompanyCompetitors, getEntitySources } from "@/lib/api";
import EvidenceDrawer from "@/components/EvidenceDrawer";
import PriceChart from "@/components/PriceChart";
import { StatCard, EmptyState, SkeletonBlock } from "@/components/ui";

const TABS = ["overview", "brands", "skus", "competitors", "sources"] as const;
type Tab = (typeof TABS)[number];

export default function CompanyDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const [company, setCompany] = useState<any>(null);
  const [brands, setBrands] = useState<any[]>([]);
  const [skus, setSkus] = useState<any[]>([]);
  const [competitors, setCompetitors] = useState<any[]>([]);
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  useEffect(() => {
    if (!id) return;
    Promise.all([
      getCompany(id),
      getCompanyBrands(id),
      getCompanySkus(id),
      getCompanyCompetitors(id),
      getEntitySources("company", id),
    ])
      .then(([c, b, s, comp, src]) => {
        setCompany(c);
        setBrands(b);
        setSkus(s);
        setCompetitors(comp.competitors || []);
        setSources(src.sources || []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-7xl space-y-6 animate-fade-in">
        <SkeletonBlock className="h-8 w-72" />
        <div className="grid grid-cols-3 gap-4">
          <SkeletonBlock className="h-24 rounded-xl" />
          <SkeletonBlock className="h-24 rounded-xl" />
          <SkeletonBlock className="h-24 rounded-xl" />
        </div>
        <SkeletonBlock className="h-64 rounded-xl" />
      </div>
    );
  }
  if (!company) {
    return (
      <EmptyState
        icon={<Building2 className="w-5 h-5" />}
        title="Company not found"
        subtitle="It may have been removed or the link is wrong"
      />
    );
  }

  return (
    <div className="max-w-7xl animate-fade-in">
      {/* Breadcrumb */}
      <Link
        href="/companies"
        className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-slate-600 mb-4 transition-colors"
      >
        <ChevronLeft className="w-4 h-4" /> Companies
      </Link>

      {/* Hero */}
      <div className="flex flex-wrap items-center gap-4 mb-7">
        <div className="w-14 h-14 rounded-2xl bg-brand-50 text-brand-700 ring-1 ring-brand-100 flex items-center justify-center text-lg font-bold uppercase shrink-0">
          {company.name.slice(0, 2)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">{company.name}</h1>
            <EvidenceDrawer entityType="company" entityId={company.id} label="Source evidence" />
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            {company.ownership_type && (
              <span className="badge badge-blue capitalize">{company.ownership_type.name}</span>
            )}
            {company.is_listed && <span className="badge badge-green">Listed</span>}
            {company.is_global && <span className="badge badge-purple">Global</span>}
            {company.headquarters_region && (
              <span className="badge badge-slate">{company.headquarters_region.name}</span>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-200 mb-6 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`tab ${activeTab === tab ? "tab-active" : "tab-inactive"}`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
            {tab === "brands" && <Count n={brands.length} />}
            {tab === "skus" && <Count n={skus.length} />}
            {tab === "competitors" && <Count n={competitors.length} />}
            {tab === "sources" && <Count n={sources.length} />}
          </button>
        ))}
      </div>

      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Quick stats */}
          <div className="grid grid-cols-3 gap-4">
            <StatCard label="Brands" value={brands.length} color="green" />
            <StatCard label="Active SKUs" value={skus.length} color="yellow" />
            <StatCard label="Competitors" value={competitors.length} color="pink" />
          </div>

          {/* Profile card */}
          <div className="card p-5 space-y-3">
            <h3 className="font-semibold text-slate-800 text-sm">Company Profile</h3>
            {company.website && (
              <div className="text-sm">
                <span className="text-slate-400">Website:</span>{" "}
                <a
                  href={company.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-brand-600 hover:underline inline-flex items-center gap-1"
                >
                  {company.website.replace(/^https?:\/\//, "")}
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            )}
            {company.parent_company && (
              <div className="text-sm">
                <span className="text-slate-400">Parent:</span> {company.parent_company}
              </div>
            )}
            {company.description && (
              <p className="text-sm text-slate-600 leading-relaxed">{company.description}</p>
            )}
            <div className="text-xs text-slate-400 pt-2 border-t border-slate-100">
              Confidence: <span className="font-medium capitalize">{company.confidence}</span>
              {company.updated_at && <> · Last updated {new Date(company.updated_at).toLocaleDateString()}</>}
            </div>
          </div>

          {/* Price charts */}
          {skus.length > 0 && (
            <div>
              <h3 className="font-semibold text-sm text-slate-700 mb-3">Price Trends</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {skus.slice(0, 4).map((sku) => (
                  <PriceChart
                    key={sku.id}
                    skuId={sku.id}
                    skuName={`${sku.variant || ""} ${sku.pack_size}${sku.unit}`}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === "brands" && (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {brands.map((b) => (
            <div key={b.id} className="card card-hover p-5">
              <div className="font-semibold text-slate-900">{b.name}</div>
              {b.description && <div className="text-sm text-slate-500 mt-1">{b.description}</div>}
            </div>
          ))}
          {brands.length === 0 && (
            <EmptyState title="No brands found" subtitle="Brand data hasn't been added yet" />
          )}
        </div>
      )}

      {activeTab === "skus" && (
        <div className="card overflow-x-auto">
          <table className="table-clean">
            <thead>
              <tr>
                <th>Product</th>
                <th>Variant</th>
                <th className="!text-right">Pack</th>
                <th className="!text-right">MRP</th>
                <th className="!text-right">Price</th>
                <th className="!text-right">Fat %</th>
                <th className="!text-right">Protein %</th>
                <th>Status</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {skus.map((s) => (
                <tr key={s.id}>
                  <td className="font-medium text-slate-800">{s.product_name || s.variant || "—"}</td>
                  <td>{s.variant || "—"}</td>
                  <td className="text-right tabular-nums">{s.pack_size} {s.unit}</td>
                  <td className="text-right tabular-nums">₹{s.mrp}</td>
                  <td className="text-right tabular-nums font-medium text-slate-800">₹{s.selling_price}</td>
                  <td className="text-right tabular-nums">{s.fat_percent ?? "—"}</td>
                  <td className="text-right tabular-nums">{s.protein_percent ?? "—"}</td>
                  <td>
                    <span
                      className={`badge ${
                        s.status === "active" ? "badge-green" : s.status === "new" ? "badge-blue" : "badge-yellow"
                      }`}
                    >
                      {s.status}
                    </span>
                  </td>
                  <td>
                    <EvidenceDrawer entityType="sku" entityId={s.id} label="Evidence" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {skus.length === 0 && (
            <div className="p-8 text-center">
              <EmptyState title="No SKUs found" subtitle="SKU data hasn't been added yet" />
            </div>
          )}
        </div>
      )}

      {activeTab === "competitors" && (
        <div className="grid gap-3">
          {competitors.map((comp: any, i: number) => (
            <Link
              key={i}
              href={`/companies/${comp.company.id}`}
              className="card card-hover p-4 flex items-center justify-between gap-4"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-brand-50 text-brand-700 ring-1 ring-brand-100 flex items-center justify-center text-sm font-bold uppercase">
                  {comp.company.name.slice(0, 2)}
                </div>
                <div>
                  <div className="font-semibold text-slate-900">{comp.company.name}</div>
                  <div className="text-xs text-slate-400 capitalize">
                    {comp.company.ownership_type || "—"} · {comp.company.headquarters_region || "—"}
                  </div>
                </div>
              </div>
              <div className="flex gap-6 text-sm">
                <div className="text-center">
                  <div className="font-bold text-brand-700 tabular-nums">
                    {Math.round(comp.category_overlap * 100)}%
                  </div>
                  <div className="text-[11px] text-slate-400 uppercase tracking-wide">Category</div>
                </div>
                <div className="text-center">
                  <div className="font-bold text-sky-600 tabular-nums">
                    {Math.round(comp.region_overlap * 100)}%
                  </div>
                  <div className="text-[11px] text-slate-400 uppercase tracking-wide">Region</div>
                </div>
              </div>
            </Link>
          ))}
          {competitors.length === 0 && (
            <EmptyState title="No competitors found" subtitle="No overlapping categories or regions detected" />
          )}
        </div>
      )}

      {activeTab === "sources" && (
        <div className="grid gap-3">
          {sources.map((src) => (
            <div key={src.id} className="card p-4">
              <div className="flex items-center justify-between mb-2">
                <span
                  className={`badge ${
                    src.confidence === "high"
                      ? "badge-green"
                      : src.confidence === "medium"
                      ? "badge-yellow"
                      : "badge-purple"
                  }`}
                >
                  {src.confidence || "unknown"}
                </span>
                <span className="text-xs text-slate-400 capitalize">{src.source_type?.replace("_", " ")}</span>
              </div>
              {src.extracted_fact && <div className="text-sm text-slate-700 mb-2">{src.extracted_fact}</div>}
              {src.source_url && (
                <a
                  href={src.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-brand-600 hover:underline text-xs break-all inline-flex items-center gap-1"
                >
                  {src.source_url} <ExternalLink className="w-3 h-3 shrink-0" />
                </a>
              )}
              <div className="flex gap-3 mt-2 text-xs text-slate-400">
                {src.extraction_date && <span>Extracted: {src.extraction_date}</span>}
                {src.last_verified && <span>Verified: {src.last_verified}</span>}
              </div>
            </div>
          ))}
          {sources.length === 0 && (
            <EmptyState title="No sources recorded" subtitle="Evidence will appear here as data is collected" />
          )}
        </div>
      )}
    </div>
  );
}

function Count({ n }: { n: number }) {
  return n > 0 ? <span className="ml-1.5 text-xs text-slate-400 font-normal">{n}</span> : null;
}
