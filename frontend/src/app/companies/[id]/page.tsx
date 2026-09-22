"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getCompany, getCompanyBrands, getCompanySkus, getCompanyCompetitors, getEntitySources } from "@/lib/api";
import EvidenceDrawer from "@/components/EvidenceDrawer";
import PriceChart from "@/components/PriceChart";

export default function CompanyDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const [company, setCompany] = useState<any>(null);
  const [brands, setBrands] = useState<any[]>([]);
  const [skus, setSkus] = useState<any[]>([]);
  const [competitors, setCompetitors] = useState<any[]>([]);
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"overview" | "brands" | "skus" | "competitors" | "sources">("overview");

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

  if (loading) return <div className="text-gray-500">Loading...</div>;
  if (!company) return <div className="text-red-500">Company not found</div>;

  // Group SKUs by product
  const skusByProduct: Record<string, any[]> = {};
  skus.forEach((s) => {
    const key = s.variant || "default";
    if (!skusByProduct[key]) skusByProduct[key] = [];
    skusByProduct[key].push(s);
  });

  return (
    <div>
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-2xl font-bold">{company.name}</h1>
          <EvidenceDrawer entityType="company" entityId={company.id} label="Company Source" />
        </div>
        <div className="flex gap-2">
          {company.ownership_type && (
            <span className="badge badge-blue capitalize">{company.ownership_type.name}</span>
          )}
          {company.is_listed && <span className="badge badge-green">Listed</span>}
          {company.is_global && <span className="badge badge-purple">Global</span>}
          {company.headquarters_region && (
            <span className="badge badge-yellow">{company.headquarters_region.name}</span>
          )}
        </div>
      </div>

      <div className="flex gap-1 border-b mb-6 overflow-x-auto">
        {(["overview", "brands", "skus", "competitors", "sources"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
              activeTab === tab
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
            {tab === "skus" && <span className="ml-1 text-gray-400">({skus.length})</span>}
            {tab === "competitors" && <span className="ml-1 text-gray-400">({competitors.length})</span>}
            {tab === "sources" && <span className="ml-1 text-gray-400">({sources.length})</span>}
          </button>
        ))}
      </div>

      {activeTab === "overview" && (
        <div className="space-y-4">
          <div className="card p-4 space-y-3">
            {company.website && (
              <div>
                <span className="text-gray-500 text-sm">Website:</span>{" "}
                <a href={company.website} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                  {company.website}
                </a>
              </div>
            )}
            {company.parent_company && (
              <div>
                <span className="text-gray-500 text-sm">Parent:</span> {company.parent_company}
              </div>
            )}
            {company.description && (
              <div className="text-sm text-gray-600">{company.description}</div>
            )}
            <div className="text-xs text-gray-400 mt-4">
              Confidence: {company.confidence} | Last updated: {company.updated_at}
            </div>
          </div>

          {/* Quick stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="card p-4 text-center">
              <div className="text-xl font-bold text-blue-600">{brands.length}</div>
              <div className="text-sm text-gray-500">Brands</div>
            </div>
            <div className="card p-4 text-center">
              <div className="text-xl font-bold text-blue-600">{skus.length}</div>
              <div className="text-sm text-gray-500">Active SKUs</div>
            </div>
            <div className="card p-4 text-center">
              <div className="text-xl font-bold text-blue-600">{competitors.length}</div>
              <div className="text-sm text-gray-500">Competitors</div>
            </div>
          </div>

          {/* Price charts for first few SKUs */}
          {skus.length > 0 && (
            <div>
              <h3 className="font-semibold text-sm mb-3">Price Trends</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {skus.slice(0, 4).map((sku) => (
                  <PriceChart key={sku.id} skuId={sku.id} skuName={`${sku.variant || ""} ${sku.pack_size}${sku.unit}`} />
                ))}
              </div>
            </div>
          )}
              <div className="text-sm text-gray-500">Competitors</div>
            </div>
          </div>
        </div>
      )}

      {activeTab === "brands" && (
        <div className="grid gap-3 md:grid-cols-2">
          {brands.map((b) => (
            <div key={b.id} className="card p-4">
              <div className="font-semibold">{b.name}</div>
              {b.description && <div className="text-sm text-gray-500 mt-1">{b.description}</div>}
            </div>
          ))}
          {brands.length === 0 && <div className="text-gray-500">No brands found</div>}
        </div>
      )}

      {activeTab === "skus" && (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-3">Product</th>
                <th className="text-left p-3">Variant</th>
                <th className="text-right p-3">Pack</th>
                <th className="text-right p-3">MRP</th>
                <th className="text-right p-3">Price</th>
                <th className="text-right p-3">Fat %</th>
                <th className="text-right p-3">Protein %</th>
                <th className="text-left p-3">Status</th>
                <th className="text-left p-3">Source</th>
              </tr>
            </thead>
            <tbody>
              {skus.map((s) => (
                <tr key={s.id} className="border-t hover:bg-gray-50">
                  <td className="p-3">{s.product_name || s.variant || "—"}</td>
                  <td className="p-3">{s.variant || "—"}</td>
                  <td className="p-3 text-right">{s.pack_size} {s.unit}</td>
                  <td className="p-3 text-right">₹{s.mrp}</td>
                  <td className="p-3 text-right">₹{s.selling_price}</td>
                  <td className="p-3 text-right">{s.fat_percent || "—"}%</td>
                  <td className="p-3 text-right">{s.protein_percent || "—"}%</td>
                  <td className="p-3">
                    <span className={`badge ${s.status === "active" ? "badge-green" : s.status === "new" ? "badge-blue" : "badge-yellow"}`}>
                      {s.status}
                    </span>
                  </td>
                  <td className="p-3">
                    <EvidenceDrawer entityType="sku" entityId={s.id} label="Evidence" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {skus.length === 0 && <div className="p-4 text-gray-500 text-center">No SKUs found</div>}
        </div>
      )}

      {activeTab === "competitors" && (
        <div className="grid gap-3">
          {competitors.map((comp: any, i: number) => (
            <div key={i} className="card p-4">
              <div className="flex items-center justify-between">
                <div>
                  <a href={`/companies/${comp.company.id}`} className="font-semibold text-blue-600 hover:underline">
                    {comp.company.name}
                  </a>
                  <div className="text-sm text-gray-500">
                    {comp.company.ownership_type || "—"} | {comp.company.headquarters_region || "—"}
                  </div>
                </div>
                <div className="flex gap-4 text-sm">
                  <div className="text-center">
                    <div className="font-medium">{Math.round(comp.category_overlap * 100)}%</div>
                    <div className="text-gray-400 text-xs">Category</div>
                  </div>
                  <div className="text-center">
                    <div className="font-medium">{Math.round(comp.region_overlap * 100)}%</div>
                    <div className="text-gray-400 text-xs">Region</div>
                  </div>
                </div>
              </div>
            </div>
          ))}
          {competitors.length === 0 && <div className="text-gray-500">No competitors found</div>}
        </div>
      )}

      {activeTab === "sources" && (
        <div className="grid gap-3">
          {sources.map((src) => (
            <div key={src.id} className="card p-4">
              <div className="flex items-center justify-between mb-2">
                <span className={`badge ${
                  src.confidence === "high" ? "badge-green" :
                  src.confidence === "medium" ? "badge-yellow" : "badge-purple"
                }`}>
                  {src.confidence || "unknown"}
                </span>
                <span className="text-xs text-gray-400">{src.source_type?.replace("_", " ")}</span>
              </div>
              {src.extracted_fact && (
                <div className="text-sm text-gray-700 mb-2">{src.extracted_fact}</div>
              )}
              {src.source_url && (
                <a href={src.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-xs break-all">
                  {src.source_url}
                </a>
              )}
              <div className="flex gap-3 mt-2 text-xs text-gray-400">
                {src.extraction_date && <span>Extracted: {src.extraction_date}</span>}
                {src.last_verified && <span>Verified: {src.last_verified}</span>}
              </div>
            </div>
          ))}
          {sources.length === 0 && <div className="text-gray-500">No sources recorded</div>}
        </div>
      )}
    </div>
  );
}
