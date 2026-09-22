"use client";

import { useState } from "react";
import { search } from "@/lib/api";
import EvidenceDrawer from "@/components/EvidenceDrawer";

const ENTITY_TYPES = [
  { value: "", label: "All" },
  { value: "company", label: "Companies" },
  { value: "brand", label: "Brands" },
  { value: "product", label: "Products" },
  { value: "sku", label: "SKUs" },
  { value: "retailer", label: "Retailers" },
];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [entityType, setEntityType] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const res = await search(query, entityType || undefined);
      setResults(res.results || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const getLink = (r: any) => {
    switch (r.type) {
      case "company": return `/companies/${r.id}`;
      case "brand": return `/companies/${r.company_id}`;
      default: return "#";
    }
  };

  const getTypeBadge = (type: string) => {
    switch (type) {
      case "company": return "badge-blue";
      case "brand": return "badge-green";
      case "product": return "badge-yellow";
      case "sku": return "badge-purple";
      case "retailer": return "badge-green";
      default: return "badge-blue";
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Search</h1>
      <p className="text-gray-500 mb-6">Search across companies, brands, products, SKUs, and retailers</p>

      <div className="card p-4 mb-6">
        <div className="flex gap-4">
          <input
            type="text"
            placeholder="Search dairy companies, products, SKUs..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="input flex-1"
          />
          <select
            value={entityType}
            onChange={(e) => setEntityType(e.target.value)}
            className="input"
          >
            {ENTITY_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          <button onClick={handleSearch} disabled={loading} className="btn-primary">
            {loading ? "Searching..." : "Search"}
          </button>
        </div>

        <div className="flex gap-2 mt-3">
          <button onClick={() => { setQuery("Amul"); handleSearch(); }} className="text-xs text-gray-500 hover:text-blue-600">
            Try: "Amul"
          </button>
          <span className="text-gray-300">|</span>
          <button onClick={() => { setQuery("paneer"); }} className="text-xs text-gray-500 hover:text-blue-600">
            Try: "paneer"
          </button>
          <span className="text-gray-300">|</span>
          <button onClick={() => { setQuery("toned"); }} className="text-xs text-gray-500 hover:text-blue-600">
            Try: "toned"
          </button>
          <span className="text-gray-300">|</span>
          <button onClick={() => { setQuery("ghee"); }} className="text-xs text-gray-500 hover:text-blue-600">
            Try: "ghee"
          </button>
        </div>
      </div>

      {/* Results */}
      {searched && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm text-gray-500">
              {results.length} result{results.length !== 1 ? "s" : ""} for "{query}"
            </div>
          </div>

          <div className="grid gap-2">
            {results.map((r, i) => (
              <div key={i} className="card p-4 hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`badge ${getTypeBadge(r.type)}`}>{r.type}</span>
                    <div>
                      <a
                        href={getLink(r)}
                        className="font-medium text-blue-600 hover:underline"
                      >
                        {r.name || r.variant || "Unknown"}
                      </a>
                      {r.pack_size && (
                        <span className="text-sm text-gray-500 ml-2">
                          {r.pack_size} {r.unit}
                        </span>
                      )}
                      {r.company_id && (
                        <span className="text-xs text-gray-400 ml-2">
                          Company #{r.company_id}
                        </span>
                      )}
                    </div>
                  </div>
                  <div>
                    {r.type === "sku" && (
                      <EvidenceDrawer entityType="sku" entityId={r.id} label="Evidence" />
                    )}
                    {r.type === "company" && (
                      <EvidenceDrawer entityType="company" entityId={r.id} label="Evidence" />
                    )}
                  </div>
                </div>
              </div>
            ))}

            {results.length === 0 && !loading && (
              <div className="text-center text-gray-400 py-12">
                <div className="text-lg mb-2">No results found</div>
                <div className="text-sm">Try a different search term or filter</div>
              </div>
            )}
          </div>
        </div>
      )}

      {!searched && (
        <div className="text-center text-gray-400 py-16">
          <div className="text-4xl mb-4">&#128270;</div>
          <div className="text-lg mb-2">Search the dairy intelligence database</div>
          <div className="text-sm">Find companies, brands, products, SKUs, and retailers</div>
        </div>
      )}
    </div>
  );
}
