"use client";

import { useEffect, useState } from "react";
import { getSkuPriceHistory } from "@/lib/api";

interface PriceChartProps {
  skuId: number;
  skuName?: string;
}

export default function PriceChart({ skuId, skuName }: PriceChartProps) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSkuPriceHistory(skuId)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [skuId]);

  if (loading) return <div className="text-gray-400 text-sm">Loading price history...</div>;
  if (!data || data.history?.length === 0) {
    return <div className="text-gray-400 text-sm">No price history available</div>;
  }

  const history = data.history || [];
  const prices = history.map((h: any) => h.selling_price || h.mrp).filter(Boolean);
  const maxPrice = Math.max(...prices);
  const minPrice = Math.min(...prices);
  const range = maxPrice - minPrice || 1;

  const chartWidth = 300;
  const chartHeight = 120;
  const padding = 30;

  const points = history
    .filter((h: any) => h.selling_price || h.mrp)
    .map((h: any, i: number, arr: any[]) => {
      const price = h.selling_price || h.mrp;
      const x = padding + (i / (arr.length - 1 || 1)) * (chartWidth - padding * 2);
      const y = chartHeight - padding - ((price - minPrice) / range) * (chartHeight - padding * 2);
      return { x, y, price, date: h.recorded_date };
    });

  const pathD = points.length > 1
    ? `M ${points.map((p: any) => `${p.x},${p.y}`).join(" L ")}`
    : points.length === 1
    ? `M ${points[0].x},${points[0].y} L ${points[0].x + 1},${points[0].y}`
    : "";

  const areaD = pathD
    ? `${pathD} L ${points[points.length - 1].x},${chartHeight - padding} L ${points[0].x},${chartHeight - padding} Z`
    : "";

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium">
          Price History{skuName ? `: ${skuName}` : ""}
        </h3>
        <div className="text-xs text-gray-400">
          Current: ₹{data.current_price || data.current_mrp}
        </div>
      </div>

      <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="w-full" style={{ height: 120 }}>
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((pct) => {
          const y = chartHeight - padding - pct * (chartHeight - padding * 2);
          const price = minPrice + pct * range;
          return (
            <g key={pct}>
              <line
                x1={padding}
                y1={y}
                x2={chartWidth - padding}
                y2={y}
                stroke="#e5e7eb"
                strokeWidth="0.5"
              />
              <text
                x={padding - 4}
                y={y + 3}
                textAnchor="end"
                fontSize="8"
                fill="#9ca3af"
              >
                ₹{Math.round(price)}
              </text>
            </g>
          );
        })}

        {/* Area */}
        {areaD && (
          <path d={areaD} fill="rgba(59, 130, 246, 0.1)" />
        )}

        {/* Line */}
        {pathD && (
          <path d={pathD} fill="none" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round" />
        )}

        {/* Points */}
        {points.map((p: any, i: number) => (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r="3" fill="#3b82f6" stroke="white" strokeWidth="1" />
            {i === 0 || i === points.length - 1 ? (
              <text
                x={p.x}
                y={chartHeight - 8}
                textAnchor="middle"
                fontSize="7"
                fill="#9ca3af"
              >
                {p.date?.slice(5) || ""}
              </text>
            ) : null}
          </g>
        ))}

        {/* No data message */}
        {points.length === 0 && (
          <text
            x={chartWidth / 2}
            y={chartHeight / 2}
            textAnchor="middle"
            fontSize="10"
            fill="#9ca3af"
          >
            No price data
          </text>
        )}
      </svg>

      {history.length > 0 && (
        <div className="flex justify-between text-xs text-gray-400 mt-2">
          <span>Min: ₹{minPrice}</span>
          <span>{history.length} records</span>
          <span>Max: ₹{maxPrice}</span>
        </div>
      )}
    </div>
  );
}
