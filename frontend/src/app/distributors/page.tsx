"use client";

import { useEffect, useState } from "react";
import { getDistributors } from "@/lib/api";

const STATES = [
  "Delhi NCR", "Punjab", "Haryana", "Uttar Pradesh", "Rajasthan",
  "Maharashtra", "Gujarat", "Madhya Pradesh", "Goa",
  "Karnataka", "Tamil Nadu", "Andhra Pradesh", "Telangana", "Kerala",
];

export default function DistributorsPage() {
  const [distributors, setDistributors] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");

  useEffect(() => {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    if (stateFilter) params.state = stateFilter;
    if (typeFilter) params.distributor_type = typeFilter;
    if (channelFilter) params.channel = channelFilter;
    getDistributors(params)
      .then(setDistributors)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [search, stateFilter, typeFilter, channelFilter]);

  const typeColors: Record<string, string> = {
    national: "badge-green",
    regional: "badge-blue",
    local: "badge-yellow",
  };

  const channelColors: Record<string, string> = {
    general_trade: "badge-blue",
    modern_trade: "badge-green",
    ecommerce: "badge-purple",
    quick_commerce: "badge-yellow",
    supermarket: "badge-green",
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Distributors</h1>
      <p className="text-gray-500 mb-6">Distribution network intelligence across India</p>

      <div className="flex flex-wrap gap-3 mb-6">
        <input
          type="text"
          placeholder="Search distributors..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input flex-1 min-w-[200px]"
        />
        <select value={stateFilter} onChange={(e) => setStateFilter(e.target.value)} className="input">
          <option value="">All States</option>
          {STATES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="input">
          <option value="">All Types</option>
          <option value="national">National</option>
          <option value="regional">Regional</option>
          <option value="local">Local</option>
        </select>
        <select value={channelFilter} onChange={(e) => setChannelFilter(e.target.value)} className="input">
          <option value="">All Channels</option>
          <option value="general_trade">General Trade</option>
          <option value="modern_trade">Modern Trade</option>
          <option value="ecommerce">E-commerce</option>
          <option value="quick_commerce">Quick Commerce</option>
          <option value="supermarket">Supermarket</option>
        </select>
      </div>

      {loading ? (
        <div className="text-gray-500">Loading...</div>
      ) : distributors.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <div className="text-lg mb-2">No distributors found</div>
          <div className="text-sm">Try adjusting your filters</div>
        </div>
      ) : (
        <div className="grid gap-3">
          {distributors.map((d) => (
            <div key={d.id} className="card p-4 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-lg">{d.name}</span>
                    <span className={`badge ${typeColors[d.type] || "badge-blue"}`}>
                      {d.type}
                    </span>
                    <span className={`badge ${channelColors[d.channel] || "badge-blue"}`}>
                      {d.channel?.replace(/_/g, " ")}
                    </span>
                  </div>
                  <div className="text-sm text-gray-500">
                    {d.territory && <span>{d.territory}</span>}
                    {d.city && d.state && <span> | {d.city}, {d.state}</span>}
                    {d.district && <span> | {d.district}</span>}
                  </div>
                  <div className="flex gap-4 mt-2 text-sm">
                    {d.retailer_count && (
                      <span className="text-gray-500">
                        <span className="font-medium">{d.retailer_count.toLocaleString()}</span> retailers
                      </span>
                    )}
                    {d.product_categories?.length > 0 && (
                      <span className="text-gray-500">
                        {d.product_categories.join(", ")}
                      </span>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <span className={`badge ${d.is_active ? "badge-green" : "badge-yellow"}`}>
                    {d.is_active ? "Active" : "Inactive"}
                  </span>
                  <div className="text-xs text-gray-400 mt-1">
                    Confidence: {d.confidence}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
