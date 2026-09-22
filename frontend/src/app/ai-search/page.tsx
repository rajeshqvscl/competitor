"use client";

import { useState } from "react";
import { aiSearch } from "@/lib/api";
import EvidenceDrawer from "@/components/EvidenceDrawer";

const EXAMPLE_QUERIES = [
  "Show listed dairy companies in South India",
  "Compare paneer SKUs across all companies",
  "Find cooperative competitors selling milk in Delhi",
  "Which companies sell ghee in quick commerce?",
  "Show unlisted dairy players with cheese products",
  "Find companies with retail presence in Maharashtra",
  "Compare 500ml milk SKUs across brands",
  "Show all yogurt products from listed companies",
];

export default function AiSearchPage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [searchHistory, setSearchHistory] = useState<string[]>([]);

  const handleSearch = async (searchQuery?: string) => {
    const q = searchQuery || query;
    if (!q.trim()) return;
    setLoading(true);
    setSearchHistory((prev) => [q, ...prev.slice(0, 9)]);
    try {
      const res = await aiSearch(q);
      setResult(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">AI-Powered Search</h1>
      <p className="text-gray-500 mb-6">Ask questions in natural language about dairy competitors</p>

      <div className="card p-4 mb-6">
        <div className="flex gap-4">
          <input
            type="text"
            placeholder='e.g. "Show listed dairy companies in South India selling paneer"'
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="input flex-1 text-base"
          />
          <button onClick={() => handleSearch()} disabled={loading} className="btn-primary px-6">
            {loading ? "Searching..." : "Ask"}
          </button>
        </div>

        {/* Example queries */}
        <div className="mt-3">
          <div className="text-xs text-gray-400 mb-2">Try asking:</div>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_QUERIES.map((eq, i) => (
              <button
                key={i}
                onClick={() => { setQuery(eq); handleSearch(eq); }}
                className="text-xs text-blue-600 hover:text-blue-800 bg-blue-50 px-2 py-1 rounded"
              >
                {eq}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Search history */}
      {searchHistory.length > 0 && (
        <div className="mb-6">
          <div className="text-xs text-gray-400 mb-2">Recent queries:</div>
          <div className="flex gap-2 flex-wrap">
            {searchHistory.map((h, i) => (
              <button
                key={i}
                onClick={() => { setQuery(h); handleSearch(h); }}
                className="text-xs text-gray-600 hover:text-blue-600 bg-gray-100 px-2 py-1 rounded"
              >
                {h}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="card p-4 bg-blue-50">
            <div className="text-sm font-medium text-blue-800">{result.summary}</div>
            {Object.keys(result.filters).length > 0 && (
              <div className="text-xs text-blue-600 mt-2">
                Detected filters:{" "}
                {Object.entries(result.filters)
                  .filter(([, v]) => v)
                  .map(([k, v]) => `${k}="${v}"`)
                  .join(", ")}
              </div>
            )}
          </div>

          {/* Companies */}
          {result.results?.companies?.length > 0 && (
            <div>
              <h2 className="font-semibold mb-3">Companies ({result.results.companies.length})</h2>
              <div className="grid gap-2">
                {result.results.companies.map((c: any) => (
                  <a
                    key={c.id}
                    href={`/companies/${c.id}`}
                    className="card p-4 hover:shadow-md transition-shadow block"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-semibold">{c.name}</div>
                        <div className="text-sm text-gray-500">
                          {c.headquarters_region || "—"}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        {c.ownership_type && (
                          <span className="badge badge-blue capitalize">{c.ownership_type}</span>
                        )}
                        {c.is_listed && <span className="badge badge-green">Listed</span>}
                        {c.is_global && <span className="badge badge-purple">Global</span>}
                      </div>
                    </div>
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* SKUs */}
          {result.results?.skus?.length > 0 && (
            <div>
              <h2 className="font-semibold mb-3">SKUs ({result.results.skus.length})</h2>
              <div className="card overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left p-3">Company</th>
                      <th className="text-left p-3">Brand</th>
                      <th className="text-left p-3">Category</th>
                      <th className="text-left p-3">Variant</th>
                      <th className="text-right p-3">Pack</th>
                      <th className="text-right p-3">MRP</th>
                      <th className="text-right p-3">Price</th>
                      <th className="text-left p-3">Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.results.skus.map((s: any) => (
                      <tr key={s.id} className="border-t hover:bg-gray-50">
                        <td className="p-3">{s.company}</td>
                        <td className="p-3">{s.brand}</td>
                        <td className="p-3">{s.category}</td>
                        <td className="p-3">{s.variant || "—"}</td>
                        <td className="p-3 text-right">{s.pack_size} {s.unit}</td>
                        <td className="p-3 text-right">₹{s.mrp}</td>
                        <td className="p-3 text-right">₹{s.selling_price}</td>
                        <td className="p-3">
                          <EvidenceDrawer entityType="sku" entityId={s.id} label="Evidence" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Retailers */}
          {result.results?.retailers?.length > 0 && (
            <div>
              <h2 className="font-semibold mb-3">Retailers ({result.results.retailers.length})</h2>
              <div className="grid gap-2 md:grid-cols-2">
                {result.results.retailers.map((r: any) => (
                  <div key={r.id} className="card p-3">
                    <div className="font-medium">{r.name}</div>
                    <div className="text-sm text-gray-500 capitalize">{r.type?.replace("_", " ")}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Empty */}
          {!result.results?.companies?.length &&
           !result.results?.skus?.length &&
           !result.results?.retailers?.length && (
            <div className="text-center py-8 text-gray-400">
              No results found. Try a different query.
            </div>
          )}
        </div>
      )}

      {!result && !loading && (
        <div className="text-center text-gray-400 py-16">
          <div className="text-4xl mb-4">&#129302;</div>
          <div className="text-lg mb-2">Ask anything about dairy competitors</div>
          <div className="text-sm">The AI will search the database and provide structured answers with evidence</div>
        </div>
      )}
    </div>
  );
}
