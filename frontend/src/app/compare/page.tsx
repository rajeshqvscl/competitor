"use client";

import { useEffect, useState } from "react";
import { getCompanies, getCompanySkus, postPortfolioComparison, postSkuComparison } from "@/lib/api";

export default function ComparePage() {
  const [companies, setCompanies] = useState<any[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [portfolioResult, setPortfolioResult] = useState<any>(null);
  const [skuResults, setSkuResults] = useState<Record<number, any[]>>({});
  const [loading, setLoading] = useState(false);
  const [activeView, setActiveView] = useState<"portfolio" | "skus">("portfolio");

  useEffect(() => {
    getCompanies().then(setCompanies).catch(console.error);
  }, []);

  const toggleCompany = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const runComparison = async () => {
    if (selectedIds.length < 2) return;
    setLoading(true);
    try {
      const port = await postPortfolioComparison({ company_ids: selectedIds });
      setPortfolioResult(port);

      const skus: Record<number, any[]> = {};
      for (const cid of selectedIds) {
        const companySkus = await getCompanySkus(cid);
        skus[cid] = companySkus;
      }
      setSkuResults(skus);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const selectedCompanies = companies.filter((c) => selectedIds.includes(c.id));

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Company Comparison</h1>
      <p className="text-gray-500 mb-6">Select 2+ companies to compare side by side</p>

      {/* Company selector */}
      <div className="card p-4 mb-6">
        <div className="text-sm font-medium text-gray-700 mb-3">
          Select companies to compare ({selectedIds.length} selected)
        </div>
        <div className="flex flex-wrap gap-2 mb-4">
          {companies.map((c) => (
            <button
              key={c.id}
              onClick={() => toggleCompany(c.id)}
              className={`text-sm px-3 py-1.5 rounded-lg border transition-colors ${
                selectedIds.includes(c.id)
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-700 border-gray-300 hover:border-blue-400"
              }`}
            >
              {c.name}
              {c.ownership_type && (
                <span className="ml-1 text-xs opacity-70">
                  ({c.ownership_type.name})
                </span>
              )}
            </button>
          ))}
        </div>
        <button
          onClick={runComparison}
          disabled={selectedIds.length < 2 || loading}
          className="btn-primary disabled:opacity-50"
        >
          {loading ? "Comparing..." : `Compare ${selectedIds.length} Companies`}
        </button>
      </div>

      {/* Results */}
      {portfolioResult && (
        <div>
          <div className="flex gap-1 border-b mb-6">
            <button
              onClick={() => setActiveView("portfolio")}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeView === "portfolio"
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500"
              }`}
            >
              Portfolio
            </button>
            <button
              onClick={() => setActiveView("skus")}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeView === "skus"
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500"
              }`}
            >
              All SKUs
            </button>
          </div>

          {activeView === "portfolio" && (
            <div className="card overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left p-3">Category</th>
                    {selectedCompanies.map((c) => (
                      <th key={c.id} className="text-center p-3 min-w-[120px]">
                        <div className="font-medium">{c.name}</div>
                        <div className="text-xs text-gray-400 font-normal">
                          {c.ownership_type?.name || "—"}
                        </div>
                      </th>
                    ))}
                    <th className="text-center p-3">Presence</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolioResult.comparison?.map((row: any, i: number) => {
                    const presentCount = selectedIds.filter((cid) => row.companies[cid]).length;
                    return (
                      <tr key={i} className="border-t hover:bg-gray-50">
                        <td className="p-3 font-medium">{row.category}</td>
                        {selectedIds.map((cid) => (
                          <td key={cid} className="text-center p-3">
                            {row.companies[cid] ? (
                              <span className="text-green-600 text-lg">&#10003;</span>
                            ) : (
                              <span className="text-gray-300">&#8212;</span>
                            )}
                          </td>
                        ))}
                        <td className="text-center p-3">
                          <span className={`text-sm font-medium ${
                            presentCount === selectedIds.length ? "text-green-600" :
                            presentCount > 0 ? "text-yellow-600" : "text-red-600"
                          }`}>
                            {presentCount}/{selectedIds.length}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {activeView === "skus" && (
            <div className="space-y-6">
              {selectedCompanies.map((c) => (
                <div key={c.id}>
                  <h3 className="font-semibold mb-3">{c.name} SKUs ({skuResults[c.id]?.length || 0})</h3>
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
                        </tr>
                      </thead>
                      <tbody>
                        {skuResults[c.id]?.slice(0, 20).map((sku) => (
                          <tr key={sku.id} className="border-t">
                            <td className="p-3">{sku.product_name || sku.variant || "—"}</td>
                            <td className="p-3">{sku.variant || "—"}</td>
                            <td className="p-3 text-right">{sku.pack_size} {sku.unit}</td>
                            <td className="p-3 text-right">₹{sku.mrp}</td>
                            <td className="p-3 text-right">₹{sku.selling_price}</td>
                            <td className="p-3 text-right">{sku.fat_percent || "—"}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {(skuResults[c.id]?.length || 0) > 20 && (
                      <div className="p-3 text-center text-sm text-gray-500">
                        Showing 20 of {skuResults[c.id].length} SKUs
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {!portfolioResult && !loading && (
        <div className="text-center text-gray-400 py-16">
          <div className="text-4xl mb-4">&#128269;</div>
          <div className="text-lg mb-2">Select companies to compare</div>
          <div className="text-sm">Choose 2 or more companies from the list above</div>
        </div>
      )}
    </div>
  );
}
