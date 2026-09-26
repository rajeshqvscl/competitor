"use client";

import { useEffect, useState } from "react";
import {
  getCompanies, getCategories, getSubcategories, getRetailers,
  postCompetitorAnalysis, postPortfolioComparison, postSkuComparison,
  postRetailerOverlap, postWhiteSpace, saveAnalysis
} from "@/lib/api";
import EvidenceDrawer from "@/components/EvidenceDrawer";
import ExportButton from "@/components/ExportButton";
import GeoMap from "@/components/GeoMap";

const REGIONS = [
  { id: "north", name: "North India", states: ["Delhi NCR", "Punjab", "Haryana", "Uttar Pradesh", "Rajasthan"] },
  { id: "west", name: "West India", states: ["Maharashtra", "Gujarat", "Madhya Pradesh", "Goa"] },
  { id: "south", name: "South India", states: ["Karnataka", "Tamil Nadu", "Andhra Pradesh", "Telangana", "Kerala"] },
  { id: "east", name: "East India", states: ["West Bengal", "Bihar", "Odisha"] },
];

export default function AnalysisPage() {
  const [companies, setCompanies] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [subcategories, setSubcategories] = useState<any[]>([]);
  const [retailers, setRetailers] = useState<any[]>([]);

  const [targetCompanyId, setTargetCompanyId] = useState<number>(0);
  const [selectedRegion, setSelectedRegion] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<number>(0);
  const [selectedSubcategory, setSelectedSubcategory] = useState<number>(0);
  const [selectedChannel, setSelectedChannel] = useState("");
  const [competitorIds, setCompetitorIds] = useState<number[]>([]);

  const [competitorResult, setCompetitorResult] = useState<any>(null);
  const [portfolioResult, setPortfolioResult] = useState<any>(null);
  const [skuResult, setSkuResult] = useState<any>(null);
  const [retailerResult, setRetailerResult] = useState<any>(null);
  const [whiteSpaceResult, setWhiteSpaceResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeSection, setActiveSection] = useState<
    "competitors" | "portfolio" | "skus" | "retailers" | "geography" | "whitespace"
  >("competitors");
  const [saving, setSaving] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [saveDescription, setSaveDescription] = useState("");

  useEffect(() => {
    Promise.all([
      getCompanies(),
      getCategories(),
      getRetailers(),
    ]).then(([c, cat, r]) => {
      setCompanies(c);
      setCategories(cat);
      setRetailers(r);
    }).catch(console.error);
  }, []);

  useEffect(() => {
    if (selectedCategory) {
      getSubcategories(selectedCategory).then(setSubcategories).catch(console.error);
    }
  }, [selectedCategory]);

  const runAnalysis = async () => {
    if (!targetCompanyId) return;
    setLoading(true);
    try {
      const allIds = [targetCompanyId, ...competitorIds];
      const [comp, port, sku, ret, ws] = await Promise.all([
        postCompetitorAnalysis({
          company_id: targetCompanyId,
          category_id: selectedCategory || undefined,
        }),
        postPortfolioComparison({
          company_ids: allIds,
          category_id: selectedCategory || undefined,
        }),
        selectedSubcategory
          ? postSkuComparison({ company_ids: allIds, subcategory_id: selectedSubcategory })
          : Promise.resolve(null),
        postRetailerOverlap({ company_ids: allIds }),
        postWhiteSpace({ company_ids: allIds }),
      ]);
      setCompetitorResult(comp);
      setPortfolioResult(port);
      setSkuResult(sku);
      setRetailerResult(ret);
      setWhiteSpaceResult(ws);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const toggleCompetitor = (id: number) => {
    setCompetitorIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const addAllCompetitors = () => {
    if (!competitorResult?.competitors) return;
    setCompetitorIds(competitorResult.competitors.map((c: any) => c.company.id));
  };

  const clearCompetitors = () => setCompetitorIds([]);

  const handleSave = async () => {
    if (!saveName.trim()) return;
    setSaving(true);
    try {
      await saveAnalysis({
        name: saveName,
        description: saveDescription,
        filters: {
          company_id: targetCompanyId,
          region: selectedRegion,
          category_id: selectedCategory,
          subcategory_id: selectedSubcategory,
          channel: selectedChannel,
          competitor_ids: competitorIds,
        },
        results: {
          competitors: competitorResult?.competitors?.map((c: any) => ({
            id: c.company.id,
            name: c.company.name,
            category_overlap: c.category_overlap,
          })),
          summary: competitorResult?.summary,
        },
      });
      setShowSaveDialog(false);
      setSaveName("");
      setSaveDescription("");
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const targetCompany = companies.find((c) => c.id === targetCompanyId);

  // Build geographic data for the map
  const buildGeoData = () => {
    const geoData: Record<string, string[]> = {};
    for (const comp of companies) {
      // Simple heuristic: companies in a region have presence there
      const companyRegions = REGIONS.filter((r) => {
        // This is simplified - in production you'd fetch from the API
        return true;
      });
      // For now, use the company's headquarters to infer region
      if (comp.headquarters_region?.name) {
        const region = REGIONS.find((r) =>
          r.states.includes(comp.headquarters_region.name)
        );
        if (region) {
          geoData[comp.name] = [comp.headquarters_region.name];
        }
      }
    }
    return geoData;
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Competitor Analysis</h1>

      {/* Filters */}
      <div className="card p-4 mb-6">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Target Company</label>
            <select value={targetCompanyId} onChange={(e) => setTargetCompanyId(Number(e.target.value))} className="input w-full">
              <option value={0}>Select company</option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Region</label>
            <select value={selectedRegion} onChange={(e) => setSelectedRegion(e.target.value)} className="input w-full">
              <option value="">All regions</option>
              {REGIONS.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
            <select value={selectedCategory} onChange={(e) => setSelectedCategory(Number(e.target.value))} className="input w-full">
              <option value={0}>All categories</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Subcategory</label>
            <select value={selectedSubcategory} onChange={(e) => setSelectedSubcategory(Number(e.target.value))} className="input w-full">
              <option value={0}>All subcategories</option>
              {subcategories.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Channel</label>
            <select value={selectedChannel} onChange={(e) => setSelectedChannel(e.target.value)} className="input w-full">
              <option value="">All channels</option>
              <option value="general_trade">General Trade</option>
              <option value="modern_trade">Modern Trade</option>
              <option value="ecommerce">E-commerce</option>
              <option value="quick_commerce">Quick Commerce</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={runAnalysis}
            disabled={!targetCompanyId || loading}
            title={!targetCompanyId ? "Select a target company first" : undefined}
            className="btn-primary"
          >
            {loading ? "Analyzing..." : "Run Analysis"}
          </button>
          {!targetCompanyId && !loading && (
            <span className="text-sm text-amber-600 flex items-center gap-1.5">
              ⚠ Select a target company to enable analysis
            </span>
          )}

          {competitorResult?.competitors?.length > 0 && (
            <>
              <button onClick={addAllCompetitors} className="btn-secondary text-sm">
                Add All Competitors
              </button>
              <button onClick={clearCompetitors} className="btn-secondary text-sm">
                Clear Selection
              </button>
              <button
                onClick={() => setShowSaveDialog(true)}
                className="btn-secondary text-sm text-green-600 hover:bg-green-50"
              >
                Save Analysis
              </button>
              {competitorIds.length > 0 && (
                <span className="text-sm text-gray-500">
                  {competitorIds.length} competitor{competitorIds.length !== 1 ? "s" : ""} selected
                </span>
              )}
            </>
          )}
        </div>

        {/* Competitor quick-select */}
        {competitorResult?.competitors?.length > 0 && (
          <div className="mt-4 pt-4 border-t">
            <div className="text-xs text-gray-500 mb-2">Quick select competitors:</div>
            <div className="flex flex-wrap gap-2">
              {competitorResult.competitors.map((comp: any) => (
                <button
                  key={comp.company.id}
                  onClick={() => toggleCompetitor(comp.company.id)}
                  className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                    competitorIds.includes(comp.company.id)
                      ? "bg-blue-600 text-white border-blue-600"
                      : "bg-white text-gray-700 border-gray-300 hover:border-blue-400"
                  }`}
                >
                  {comp.company.name}
                  <span className="ml-1 text-gray-400">
                    {Math.round(comp.category_overlap * 100)}%
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Section tabs */}
      {competitorResult && (
        <div className="flex gap-1 border-b mb-6 overflow-x-auto">
          {(["competitors", "portfolio", "skus", "retailers", "geography", "whitespace"] as const).map((sec) => (
            <button
              key={sec}
              onClick={() => setActiveSection(sec)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeSection === sec
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {sec === "whitespace" ? "White Space" : sec.charAt(0).toUpperCase() + sec.slice(1)}
            </button>
          ))}
        </div>
      )}

      {/* Competitors */}
      {activeSection === "competitors" && competitorResult && (
        <div>
          <div className="card p-4 mb-4">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-500">
                Target: <span className="font-medium text-gray-900">{competitorResult.target_company?.name}</span>
                {" | "}
                {competitorResult.summary?.total_competitors} competitors found
              </div>
            </div>
          </div>
          <div className="grid gap-3">
            {competitorResult.competitors?.map((comp: any) => (
              <div key={comp.company.id} className="card p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={competitorIds.includes(comp.company.id)}
                      onChange={() => toggleCompetitor(comp.company.id)}
                      className="w-4 h-4 rounded border-gray-300"
                    />
                    <div>
                      <a href={`/companies/${comp.company.id}`} className="font-semibold text-blue-600 hover:underline">
                        {comp.company.name}
                      </a>
                      <div className="text-sm text-gray-500">
                        {comp.company.ownership_type || "—"} | {comp.company.headquarters_region || "—"}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-6 text-sm">
                    <div className="text-center">
                      <div className="font-medium">{comp.shared_categories}/{comp.total_target_categories}</div>
                      <div className="text-gray-400 text-xs">Categories</div>
                    </div>
                    <div className="text-center">
                      <div className="font-medium">{comp.shared_regions}/{comp.total_target_regions}</div>
                      <div className="text-gray-400 text-xs">Regions</div>
                    </div>
                    <div className="text-center">
                      <div className="font-medium">{Math.round(comp.category_overlap * 100)}%</div>
                      <div className="text-gray-400 text-xs">Category overlap</div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Portfolio */}
      {activeSection === "portfolio" && portfolioResult && (
        <div>
          <div className="flex justify-end mb-4">
            <ExportButton
              endpoint="portfolio"
              data={{ company_ids: [targetCompanyId, ...competitorIds] }}
              filename="portfolio_comparison.csv"
            />
          </div>
          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-3">Category</th>
                  {portfolioResult.company_ids?.map((cid: number) => {
                    const co = companies.find((c) => c.id === cid);
                    return <th key={cid} className="text-center p-3 min-w-[120px]">{co?.name || cid}</th>;
                  })}
                </tr>
              </thead>
              <tbody>
                {portfolioResult.comparison?.map((row: any, i: number) => (
                  <tr key={i} className="border-t hover:bg-gray-50">
                    <td className="p-3 font-medium">{row.category}</td>
                    {portfolioResult.company_ids?.map((cid: number) => (
                      <td key={cid} className="text-center p-3">
                        {row.companies[cid] ? (
                          <span className="text-green-600 text-lg">&#10003;</span>
                        ) : (
                          <span className="text-gray-300">&#8212;</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SKUs */}
      {activeSection === "skus" && skuResult && (
        <div>
          <div className="flex justify-end mb-4">
            {selectedSubcategory && (
              <ExportButton
                endpoint="sku-comparison"
                data={{ company_ids: [targetCompanyId, ...competitorIds], subcategory_id: selectedSubcategory }}
                filename="sku_comparison.csv"
              />
            )}
          </div>
          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-3">Company</th>
                  <th className="text-left p-3">Brand</th>
                  <th className="text-left p-3">Variant</th>
                  <th className="text-right p-3">Pack</th>
                  <th className="text-right p-3">MRP</th>
                  <th className="text-right p-3">Price</th>
                  <th className="text-right p-3">Fat %</th>
                  <th className="text-left p-3">Source</th>
                </tr>
              </thead>
              <tbody>
                {skuResult.skus?.map((sku: any) => (
                  <tr key={sku.id} className="border-t hover:bg-gray-50">
                    <td className="p-3">{sku.company_name}</td>
                    <td className="p-3">{sku.brand_name}</td>
                    <td className="p-3">{sku.variant || "—"}</td>
                    <td className="p-3 text-right">{sku.pack_size} {sku.unit}</td>
                    <td className="p-3 text-right">₹{sku.mrp}</td>
                    <td className="p-3 text-right">₹{sku.selling_price}</td>
                    <td className="p-3 text-right">{sku.fat_percent || "—"}%</td>
                    <td className="p-3">
                      <EvidenceDrawer entityType="sku" entityId={sku.id} label="Evidence" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(!skuResult.skus || skuResult.skus.length === 0) && (
              <div className="p-6 text-gray-400 text-center">
                No SKUs found. Select a subcategory for SKU-level comparison.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Retailers */}
      {activeSection === "retailers" && retailerResult && (
        <div>
          <div className="flex justify-end mb-4">
            <ExportButton
              endpoint="retailer-overlap"
              data={{ company_ids: [targetCompanyId, ...competitorIds] }}
              filename="retailer_overlap.csv"
            />
          </div>
          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-3">Retailer</th>
                  <th className="text-left p-3">Type</th>
                  {retailerResult.company_ids?.map((cid: number) => {
                    const co = companies.find((c) => c.id === cid);
                    return <th key={cid} className="text-center p-3 min-w-[120px]">{co?.name || cid}</th>;
                  })}
                </tr>
              </thead>
              <tbody>
                {retailerResult.overlap?.map((row: any, i: number) => (
                  <tr key={i} className="border-t hover:bg-gray-50">
                    <td className="p-3 font-medium">{row.retailer}</td>
                    <td className="p-3 text-gray-500 capitalize">{row.type?.replace("_", " ") || "—"}</td>
                    {retailerResult.company_ids?.map((cid: number) => (
                      <td key={cid} className="text-center p-3">
                        {row.companies[cid] ? (
                          <span className="text-green-600 text-lg">&#10003;</span>
                        ) : (
                          <span className="text-gray-300">&#8212;</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Geography */}
      {activeSection === "geography" && (
        <GeoMap
          companyRegions={buildGeoData()}
          selectedCompany={targetCompany?.name}
        />
      )}

      {/* White Space */}
      {activeSection === "whitespace" && whiteSpaceResult && (
        <div>
          <div className="card p-4 mb-4">
            <div className="text-sm text-gray-500">
              Categories and subcategories where not all selected companies have products.
              Gaps are ranked by how many companies are missing.
            </div>
          </div>
          <div className="grid gap-3">
            {whiteSpaceResult.gaps?.slice(0, 20).map((gap: any, i: number) => (
              <div key={i} className="card p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">{gap.subcategory}</div>
                    <div className="text-sm text-gray-500">{gap.category}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm">
                      <span className="text-green-600">Present:</span>{" "}
                      {gap.present_companies.join(", ") || "None"}
                    </div>
                    <div className="text-sm">
                      <span className="text-red-500">Absent:</span>{" "}
                      {gap.absent_companies.join(", ")}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!competitorResult && !loading && (
        <div className="text-center text-gray-400 py-16">
          <div className="text-lg mb-2">Select a company and click "Run Analysis"</div>
          <div className="text-sm">Compare competitors across categories, SKUs, retailers, and regions</div>
        </div>
      )}

      {/* Save Analysis Dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/30" onClick={() => setShowSaveDialog(false)} />
          <div className="relative bg-white rounded-xl shadow-xl p-6 w-96">
            <h3 className="text-lg font-semibold mb-4">Save Analysis</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                <input
                  type="text"
                  value={saveName}
                  onChange={(e) => setSaveName(e.target.value)}
                  placeholder="e.g. North India Milk Competition"
                  className="input w-full"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={saveDescription}
                  onChange={(e) => setSaveDescription(e.target.value)}
                  placeholder="Optional notes about this analysis"
                  className="input w-full"
                  rows={3}
                />
              </div>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setShowSaveDialog(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={!saveName.trim() || saving}
                  className="btn-primary disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
